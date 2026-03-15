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
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_reasoning_model: str = Field(default="gpt-5", alias="OPENAI_REASONING_MODEL")
    telegram_bot_token: str | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_default_chat_id: str | None = Field(default=None, alias="TELEGRAM_DEFAULT_CHAT_ID")
    telegram_webhook_secret: str = Field(default="change-me", alias="TELEGRAM_WEBHOOK_SECRET")
    zerodha_api_key: str | None = Field(default=None, alias="ZERODHA_API_KEY")
    zerodha_api_secret: str | None = Field(default=None, alias="ZERODHA_API_SECRET")
    zerodha_access_token: str | None = Field(default=None, alias="ZERODHA_ACCESS_TOKEN")
    default_broker: str = Field(default="PAPER", alias="DEFAULT_BROKER")


@lru_cache
def get_settings() -> Settings:
    return Settings()
