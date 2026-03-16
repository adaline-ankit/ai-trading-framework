from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="AI Trading Framework", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    database_url: str = Field(default="sqlite:///./ai_trading_framework.db", alias="DATABASE_URL")
    public_base_url: str = Field(default="http://127.0.0.1:8000", alias="PUBLIC_BASE_URL")
    bot_config_path: str = Field(default="bot.yaml", alias="BOT_CONFIG_PATH")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_reasoning_model: str = Field(default="gpt-5", alias="OPENAI_REASONING_MODEL")
    telegram_bot_token: str | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_default_chat_id: str | None = Field(default=None, alias="TELEGRAM_DEFAULT_CHAT_ID")
    telegram_webhook_secret: str = Field(default="change-me", alias="TELEGRAM_WEBHOOK_SECRET")
    session_cookie_name: str = Field(default="ai_trading_session", alias="SESSION_COOKIE_NAME")
    session_ttl_hours: int = Field(default=12, alias="SESSION_TTL_HOURS")
    auth_mode: str = Field(default="DISABLED", alias="AUTH_MODE")
    admin_email: str | None = Field(default=None, alias="ADMIN_EMAIL")
    admin_password: str | None = Field(default=None, alias="ADMIN_PASSWORD")
    admin_display_name: str = Field(default="Framework Admin", alias="ADMIN_DISPLAY_NAME")
    oidc_provider_name: str = Field(default="railway", alias="OIDC_PROVIDER_NAME")
    oidc_discovery_url: str | None = Field(default=None, alias="OIDC_DISCOVERY_URL")
    oidc_client_id: str | None = Field(default=None, alias="OIDC_CLIENT_ID")
    oidc_client_secret: str | None = Field(default=None, alias="OIDC_CLIENT_SECRET")
    oidc_redirect_uri: str | None = Field(default=None, alias="OIDC_REDIRECT_URI")
    oidc_scopes: str = Field(default="openid profile email", alias="OIDC_SCOPES")
    oidc_allowed_emails: str | None = Field(default=None, alias="OIDC_ALLOWED_EMAILS")
    oidc_allowed_domains: str | None = Field(default=None, alias="OIDC_ALLOWED_DOMAINS")
    zerodha_api_key: str | None = Field(default=None, alias="ZERODHA_API_KEY")
    zerodha_api_secret: str | None = Field(default=None, alias="ZERODHA_API_SECRET")
    zerodha_access_token: str | None = Field(default=None, alias="ZERODHA_ACCESS_TOKEN")
    default_broker: str = Field(default="PAPER", alias="DEFAULT_BROKER")


@lru_cache
def get_settings() -> Settings:
    return Settings()
