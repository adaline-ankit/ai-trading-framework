from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlencode

import httpx

from ai_trading_framework.core.runtime.settings import Settings
from ai_trading_framework.models import (
    AuthMode,
    OAuthState,
    OperatorIdentity,
    OperatorRole,
    OperatorSession,
    utcnow,
)
from ai_trading_framework.storage.sqlalchemy.repository import SQLAlchemyRunStore


@dataclass(slots=True)
class OIDCProvider:
    name: str
    discovery_url: str
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: str


class OperatorAuthError(RuntimeError):
    pass


class OperatorAuthService:
    def __init__(self, settings: Settings, store: SQLAlchemyRunStore) -> None:
        self.settings = settings
        self.store = store

    @property
    def mode(self) -> AuthMode:
        try:
            return AuthMode(self.settings.auth_mode.upper())
        except ValueError:
            return AuthMode.DISABLED

    def is_enabled(self) -> bool:
        return self.mode != AuthMode.DISABLED

    def supports_password(self) -> bool:
        return self.mode in {AuthMode.PASSWORD, AuthMode.HYBRID}

    def supports_oidc(self) -> bool:
        return self.mode in {AuthMode.OIDC, AuthMode.HYBRID} and self.oidc_provider() is not None

    def oidc_provider(self) -> OIDCProvider | None:
        if not (
            self.settings.oidc_discovery_url
            and self.settings.oidc_client_id
            and self.settings.oidc_client_secret
            and self.settings.oidc_redirect_uri
        ):
            return None
        return OIDCProvider(
            name=self.settings.oidc_provider_name,
            discovery_url=self.settings.oidc_discovery_url,
            client_id=self.settings.oidc_client_id,
            client_secret=self.settings.oidc_client_secret,
            redirect_uri=self.settings.oidc_redirect_uri,
            scopes=self.settings.oidc_scopes,
        )

    def bootstrap_password_admin(self) -> OperatorIdentity | None:
        if not (
            self.supports_password()
            and self.settings.admin_email
            and self.settings.admin_password
        ):
            return None
        operator = self.store.get_operator_by_email(self.settings.admin_email)
        password_hash = self.hash_password(self.settings.admin_password)
        if operator:
            operator.password_hash = password_hash
            operator.display_name = self.settings.admin_display_name
            operator.role = OperatorRole.ADMIN
            operator.auth_provider = operator.auth_provider or "password"
            return self.store.save_operator(operator)
        operator = OperatorIdentity(
            email=self.settings.admin_email,
            display_name=self.settings.admin_display_name,
            role=OperatorRole.ADMIN,
            auth_provider="password",
            password_hash=password_hash,
        )
        return self.store.save_operator(operator)

    def authenticate_password(self, email: str, password: str) -> OperatorSession:
        if not self.supports_password():
            raise OperatorAuthError("Password authentication is not enabled.")
        operator = self.store.get_operator_by_email(email)
        if not operator or not operator.password_hash or not self.verify_password(
            password, operator.password_hash
        ):
            raise OperatorAuthError("Invalid credentials.")
        return self._create_session(operator, auth_provider="password")

    async def begin_oidc_login(self, redirect_after: str | None = None) -> str:
        provider = self.oidc_provider()
        if not provider:
            raise OperatorAuthError("OIDC is not configured.")
        discovery = await self._load_discovery_document(provider.discovery_url)
        state_token = secrets.token_urlsafe(24)
        code_verifier = secrets.token_urlsafe(48)
        oauth_state = OAuthState(
            provider_name=provider.name,
            state_token=state_token,
            code_verifier=code_verifier,
            redirect_after=redirect_after,
            expires_at=utcnow() + timedelta(minutes=10),
        )
        self.store.save_oauth_state(oauth_state)
        params = {
            "response_type": "code",
            "client_id": provider.client_id,
            "redirect_uri": provider.redirect_uri,
            "scope": provider.scopes,
            "state": state_token,
            "code_challenge": self._pkce_challenge(code_verifier),
            "code_challenge_method": "S256",
        }
        return f"{discovery['authorization_endpoint']}?{urlencode(params)}"

    async def complete_oidc_login(self, code: str, state_token: str) -> tuple[OperatorSession, str]:
        provider = self.oidc_provider()
        if not provider:
            raise OperatorAuthError("OIDC is not configured.")
        state = self.store.pop_oauth_state(state_token)
        if not state:
            raise OperatorAuthError("Invalid or expired OIDC state.")
        if state.expires_at < utcnow():
            raise OperatorAuthError("OIDC state expired.")
        discovery = await self._load_discovery_document(provider.discovery_url)
        token_payload = await self._exchange_code_for_tokens(
            provider=provider,
            token_endpoint=discovery["token_endpoint"],
            code=code,
            code_verifier=state.code_verifier,
        )
        access_token = str(token_payload["access_token"])
        userinfo = await self._fetch_userinfo(
            userinfo_endpoint=discovery["userinfo_endpoint"],
            access_token=access_token,
        )
        operator = self._upsert_oidc_operator(provider.name, userinfo)
        session = self._create_session(
            operator,
            auth_provider=provider.name,
            metadata={
                "scopes": token_payload.get("scope", provider.scopes),
                "oidc_subject": userinfo.get("sub"),
            },
        )
        return session, state.redirect_after or "/"

    def get_operator_for_session_token(self, session_token: str | None) -> OperatorIdentity | None:
        if not session_token:
            return None
        operator_session = self.store.get_operator_session(session_token)
        if not operator_session:
            return None
        if operator_session.expires_at < utcnow():
            self.store.delete_operator_session(session_token)
            return None
        return self.store.get_operator(operator_session.operator_id)

    def logout(self, session_token: str | None) -> None:
        if session_token:
            self.store.delete_operator_session(session_token)

    def auth_summary(self) -> dict[str, object]:
        provider = self.oidc_provider()
        return {
            "enabled": self.is_enabled(),
            "mode": self.mode.value,
            "password_enabled": self.supports_password(),
            "oidc_enabled": self.supports_oidc(),
            "oidc_provider": provider.name if provider else None,
        }

    def _upsert_oidc_operator(
        self,
        provider_name: str,
        userinfo: dict[str, object],
    ) -> OperatorIdentity:
        provider_subject = str(userinfo.get("sub") or "")
        email = str(userinfo.get("email") or f"{provider_subject}@{provider_name}.local")
        if not self._email_allowed(email):
            raise OperatorAuthError("Email is not allowed to access this operator console.")
        operator = self.store.get_operator_by_subject(provider_name, provider_subject)
        if not operator:
            operator = self.store.get_operator_by_email(email)
        display_name = (
            str(userinfo.get("name") or "")
            or str(userinfo.get("preferred_username") or "")
            or email.split("@")[0]
        )
        if operator:
            operator.display_name = display_name
            operator.email = email
            operator.auth_provider = provider_name
            operator.provider_subject = provider_subject
            operator.metadata = {"userinfo": userinfo}
            operator.last_login_at = utcnow()
            return self.store.save_operator(operator)
        operator = OperatorIdentity(
            email=email,
            display_name=display_name,
            role=OperatorRole.ADMIN,
            auth_provider=provider_name,
            provider_subject=provider_subject,
            metadata={"userinfo": userinfo},
            last_login_at=utcnow(),
        )
        return self.store.save_operator(operator)

    def _create_session(
        self,
        operator: OperatorIdentity,
        *,
        auth_provider: str,
        metadata: dict[str, object] | None = None,
    ) -> OperatorSession:
        operator.last_login_at = utcnow()
        self.store.save_operator(operator)
        operator_session = OperatorSession(
            operator_id=operator.operator_id,
            session_token=secrets.token_urlsafe(32),
            auth_provider=auth_provider,
            created_at=utcnow(),
            expires_at=utcnow() + timedelta(hours=self.settings.session_ttl_hours),
            metadata=metadata or {},
        )
        return self.store.save_operator_session(operator_session)

    async def _load_discovery_document(self, discovery_url: str) -> dict[str, str]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(discovery_url)
            response.raise_for_status()
        payload = response.json()
        required_keys = {"authorization_endpoint", "token_endpoint", "userinfo_endpoint"}
        if not required_keys.issubset(payload):
            raise OperatorAuthError("OIDC discovery document is missing required endpoints.")
        return payload

    async def _exchange_code_for_tokens(
        self,
        *,
        provider: OIDCProvider,
        token_endpoint: str,
        code: str,
        code_verifier: str,
    ) -> dict[str, object]:
        basic_token = base64.b64encode(
            f"{provider.client_id}:{provider.client_secret}".encode()
        ).decode("utf-8")
        headers = {
            "Authorization": f"Basic {basic_token}",
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": provider.redirect_uri,
            "code_verifier": code_verifier,
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(token_endpoint, data=data, headers=headers)
            response.raise_for_status()
        payload = response.json()
        if "access_token" not in payload:
            raise OperatorAuthError("OIDC token exchange did not return an access token.")
        return payload

    async def _fetch_userinfo(
        self,
        *,
        userinfo_endpoint: str,
        access_token: str,
    ) -> dict[str, object]:
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(userinfo_endpoint, headers=headers)
            response.raise_for_status()
        return response.json()

    def _email_allowed(self, email: str) -> bool:
        explicit = {
            item.strip().lower()
            for item in (self.settings.oidc_allowed_emails or "").split(",")
            if item.strip()
        }
        domains = {
            item.strip().lower()
            for item in (self.settings.oidc_allowed_domains or "").split(",")
            if item.strip()
        }
        normalized = email.strip().lower()
        if explicit and normalized in explicit:
            return True
        if domains and "@" in normalized and normalized.split("@", 1)[1] in domains:
            return True
        return not explicit and not domains

    @staticmethod
    def hash_password(password: str) -> str:
        salt = secrets.token_hex(16)
        iterations = 120_000
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
        ).hex()
        return f"pbkdf2_sha256${iterations}${salt}${digest}"

    @staticmethod
    def verify_password(password: str, encoded: str) -> bool:
        try:
            _, iterations_text, salt, digest = encoded.split("$", 3)
        except ValueError:
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations_text),
        ).hex()
        return secrets.compare_digest(candidate, digest)

    @staticmethod
    def _pkce_challenge(code_verifier: str) -> str:
        digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
