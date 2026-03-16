from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Text, create_engine, delete, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from ai_trading_framework.models import (
    BrokerAuthSession,
    BrokerName,
    OAuthState,
    OperatorIdentity,
    OperatorSession,
    RunRecord,
)


class Base(DeclarativeBase):
    pass


class RunModel(Base):
    __tablename__ = "framework_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)


class OperatorModel(Base):
    __tablename__ = "framework_operators"

    operator_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    auth_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_subject: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OperatorSessionModel(Base):
    __tablename__ = "framework_operator_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    operator_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    session_token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    auth_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    meta_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class OAuthStateModel(Base):
    __tablename__ = "framework_oauth_states"

    state_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider_name: Mapped[str] = mapped_column(String(64), nullable=False)
    state_token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    code_verifier: Mapped[str] = mapped_column(String(255), nullable=False)
    redirect_after: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )


class BrokerSessionModel(Base):
    __tablename__ = "framework_broker_sessions"

    broker: Mapped[str] = mapped_column(String(32), primary_key=True)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    public_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    login_time: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_operator_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class FrameworkStateModel(Base):
    __tablename__ = "framework_state"

    state_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)


class SQLAlchemyRunStore:
    def __init__(self, database_url: str = "sqlite:///./ai_trading_framework.db") -> None:
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self.engine = create_engine(database_url, connect_args=connect_args)
        Base.metadata.create_all(self.engine)

    def save(self, run: RunRecord) -> None:
        payload = json.dumps(run.model_dump(mode="json"))
        with Session(self.engine) as session:
            session.merge(RunModel(run_id=run.run_id, symbol=run.symbol, payload=payload))
            session.commit()

    def get(self, run_id: str) -> RunRecord | None:
        with Session(self.engine) as session:
            model = session.scalar(select(RunModel).where(RunModel.run_id == run_id))
            if not model:
                return None
            return RunRecord.model_validate(json.loads(model.payload))

    def list_runs(self, limit: int = 100) -> list[RunRecord]:
        with Session(self.engine) as session:
            models = session.scalars(select(RunModel).limit(limit)).all()
            return [RunRecord.model_validate(json.loads(model.payload)) for model in models]

    def delete_run(self, run_id: str) -> None:
        with Session(self.engine) as session:
            session.execute(delete(RunModel).where(RunModel.run_id == run_id))
            session.commit()

    def clear_runs(self) -> None:
        with Session(self.engine) as session:
            session.execute(delete(RunModel))
            session.commit()

    def save_operator(self, operator: OperatorIdentity) -> OperatorIdentity:
        with Session(self.engine) as session:
            session.merge(
                OperatorModel(
                    operator_id=operator.operator_id,
                    email=operator.email,
                    display_name=operator.display_name,
                    role=operator.role.value,
                    auth_provider=operator.auth_provider,
                    provider_subject=operator.provider_subject,
                    password_hash=operator.password_hash,
                    meta_json=json.dumps(operator.metadata),
                    created_at=operator.created_at,
                    last_login_at=operator.last_login_at,
                )
            )
            session.commit()
        return operator

    def get_operator_by_email(self, email: str) -> OperatorIdentity | None:
        with Session(self.engine) as session:
            model = session.scalar(select(OperatorModel).where(OperatorModel.email == email))
            return self._hydrate_operator(model)

    def get_operator_by_subject(
        self,
        provider_name: str,
        provider_subject: str,
    ) -> OperatorIdentity | None:
        with Session(self.engine) as session:
            model = session.scalar(
                select(OperatorModel).where(
                    OperatorModel.auth_provider == provider_name,
                    OperatorModel.provider_subject == provider_subject,
                )
            )
            return self._hydrate_operator(model)

    def get_operator(self, operator_id: str) -> OperatorIdentity | None:
        with Session(self.engine) as session:
            model = session.scalar(
                select(OperatorModel).where(OperatorModel.operator_id == operator_id)
            )
            return self._hydrate_operator(model)

    def save_operator_session(self, operator_session: OperatorSession) -> OperatorSession:
        with Session(self.engine) as session:
            session.merge(
                OperatorSessionModel(
                    session_id=operator_session.session_id,
                    operator_id=operator_session.operator_id,
                    session_token=operator_session.session_token,
                    auth_provider=operator_session.auth_provider,
                    created_at=operator_session.created_at,
                    expires_at=operator_session.expires_at,
                    meta_json=json.dumps(operator_session.metadata),
                )
            )
            session.commit()
        return operator_session

    def get_operator_session(self, session_token: str) -> OperatorSession | None:
        with Session(self.engine) as session:
            model = session.scalar(
                select(OperatorSessionModel).where(
                    OperatorSessionModel.session_token == session_token
                )
            )
            return self._hydrate_operator_session(model)

    def delete_operator_session(self, session_token: str) -> None:
        with Session(self.engine) as session:
            session.execute(
                delete(OperatorSessionModel).where(
                    OperatorSessionModel.session_token == session_token
                )
            )
            session.commit()

    def save_oauth_state(self, oauth_state: OAuthState) -> OAuthState:
        with Session(self.engine) as session:
            session.merge(
                OAuthStateModel(
                    state_id=oauth_state.state_id,
                    provider_name=oauth_state.provider_name,
                    state_token=oauth_state.state_token,
                    code_verifier=oauth_state.code_verifier,
                    redirect_after=oauth_state.redirect_after,
                    created_at=oauth_state.created_at,
                    expires_at=oauth_state.expires_at,
                )
            )
            session.commit()
        return oauth_state

    def pop_oauth_state(self, state_token: str) -> OAuthState | None:
        with Session(self.engine) as session:
            model = session.scalar(
                select(OAuthStateModel).where(OAuthStateModel.state_token == state_token)
            )
            if not model:
                return None
            oauth_state = self._hydrate_oauth_state(model)
            session.delete(model)
            session.commit()
            return oauth_state

    def save_broker_session(self, broker_session: BrokerAuthSession) -> BrokerAuthSession:
        with Session(self.engine) as session:
            session.merge(
                BrokerSessionModel(
                    broker=broker_session.broker.value,
                    access_token=broker_session.access_token,
                    refresh_token=broker_session.refresh_token,
                    public_token=broker_session.public_token,
                    request_token=broker_session.request_token,
                    api_key=broker_session.api_key,
                    user_id=broker_session.user_id,
                    user_name=broker_session.user_name,
                    email=broker_session.email,
                    login_time=broker_session.login_time,
                    actor_operator_id=broker_session.actor_operator_id,
                    received_at=broker_session.received_at,
                    raw_json=json.dumps(broker_session.raw),
                )
            )
            session.commit()
        return broker_session

    def get_broker_session(self, broker: BrokerName) -> BrokerAuthSession | None:
        with Session(self.engine) as session:
            model = session.scalar(
                select(BrokerSessionModel).where(BrokerSessionModel.broker == broker.value)
            )
            return self._hydrate_broker_session(model)

    def delete_broker_session(self, broker: BrokerName) -> None:
        with Session(self.engine) as session:
            session.execute(
                delete(BrokerSessionModel).where(BrokerSessionModel.broker == broker.value)
            )
            session.commit()

    def set_state(
        self,
        namespace: str,
        key: str,
        value: dict | list | str | int | float | bool | None,
    ) -> None:
        state_key = f"{namespace}:{key}"
        payload = json.dumps(value)
        with Session(self.engine) as session:
            session.merge(FrameworkStateModel(state_key=state_key, payload=payload))
            session.commit()

    def get_state(self, namespace: str, key: str, default=None):
        state_key = f"{namespace}:{key}"
        with Session(self.engine) as session:
            model = session.scalar(
                select(FrameworkStateModel).where(FrameworkStateModel.state_key == state_key)
            )
            if not model:
                return default
            return json.loads(model.payload)

    def delete_state(self, namespace: str, key: str) -> None:
        state_key = f"{namespace}:{key}"
        with Session(self.engine) as session:
            session.execute(
                delete(FrameworkStateModel).where(FrameworkStateModel.state_key == state_key)
            )
            session.commit()

    @staticmethod
    def _hydrate_operator(model: OperatorModel | None) -> OperatorIdentity | None:
        if not model:
            return None
        return OperatorIdentity.model_validate(
            {
                "operator_id": model.operator_id,
                "email": model.email,
                "display_name": model.display_name,
                "role": model.role,
                "auth_provider": model.auth_provider,
                "provider_subject": model.provider_subject,
                "password_hash": model.password_hash,
                "metadata": json.loads(model.meta_json),
                "created_at": _ensure_utc(model.created_at),
                "last_login_at": _ensure_utc(model.last_login_at),
            }
        )

    @staticmethod
    def _hydrate_operator_session(model: OperatorSessionModel | None) -> OperatorSession | None:
        if not model:
            return None
        return OperatorSession.model_validate(
            {
                "session_id": model.session_id,
                "operator_id": model.operator_id,
                "session_token": model.session_token,
                "auth_provider": model.auth_provider,
                "created_at": _ensure_utc(model.created_at),
                "expires_at": _ensure_utc(model.expires_at),
                "metadata": json.loads(model.meta_json),
            }
        )

    @staticmethod
    def _hydrate_oauth_state(model: OAuthStateModel | None) -> OAuthState | None:
        if not model:
            return None
        return OAuthState.model_validate(
            {
                "state_id": model.state_id,
                "provider_name": model.provider_name,
                "state_token": model.state_token,
                "code_verifier": model.code_verifier,
                "redirect_after": model.redirect_after,
                "created_at": _ensure_utc(model.created_at),
                "expires_at": _ensure_utc(model.expires_at),
            }
        )

    @staticmethod
    def _hydrate_broker_session(model: BrokerSessionModel | None) -> BrokerAuthSession | None:
        if not model:
            return None
        return BrokerAuthSession.model_validate(
            {
                "broker": model.broker,
                "access_token": model.access_token,
                "refresh_token": model.refresh_token,
                "public_token": model.public_token,
                "request_token": model.request_token,
                "api_key": model.api_key,
                "user_id": model.user_id,
                "user_name": model.user_name,
                "email": model.email,
                "login_time": model.login_time,
                "actor_operator_id": model.actor_operator_id,
                "received_at": _ensure_utc(model.received_at),
                "raw": json.loads(model.raw_json),
            }
        )


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
