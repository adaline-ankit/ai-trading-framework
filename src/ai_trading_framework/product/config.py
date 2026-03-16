from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from ai_trading_framework.models import BrokerName


class BotCapabilities(BaseModel):
    portfolio: bool = True
    watchlist: bool = True
    recommendations: bool = True
    budget_investing: bool = True
    execution: bool = True
    replay: bool = True


class TelegramProductConfig(BaseModel):
    enabled: bool = True
    default_chat_id: str | None = None


class BotDefaults(BaseModel):
    watchlist: list[str] = Field(
        default_factory=lambda: ["INFY", "TCS", "RELIANCE", "HDFCBANK", "SBIN"]
    )
    recommendation_universe: list[str] = Field(
        default_factory=lambda: ["INFY", "TCS", "RELIANCE", "HDFCBANK", "SBIN"]
    )
    default_budget: float = 10000.0


class BotConfig(BaseModel):
    name: str = "my-copilot"
    mode: str = "local"
    broker: BrokerName = BrokerName.PAPER
    live_trading: bool = False
    timezone: str = "Asia/Kolkata"
    capabilities: BotCapabilities = Field(default_factory=BotCapabilities)
    telegram: TelegramProductConfig = Field(default_factory=TelegramProductConfig)
    defaults: BotDefaults = Field(default_factory=BotDefaults)


def available_templates() -> list[str]:
    template_dir = Path(__file__).with_name("templates")
    return sorted(path.stem.replace("_", "-") for path in template_dir.glob("*.yaml"))


def load_template_config(template_name: str) -> BotConfig:
    template_file = f"{template_name.replace('-', '_')}.yaml"
    template_path = Path(__file__).with_name("templates") / template_file
    if not template_path.exists():
        raise FileNotFoundError(f"Template {template_name} not found.")
    raw = yaml.safe_load(template_path.read_text()) or {}
    return BotConfig.model_validate(raw)


def default_bot_config(
    *,
    name: str,
    broker: BrokerName = BrokerName.PAPER,
    live_trading: bool = False,
    telegram_enabled: bool = True,
) -> BotConfig:
    config = BotConfig(
        name=name,
        broker=broker,
        live_trading=live_trading,
        telegram=TelegramProductConfig(enabled=telegram_enabled),
    )
    return config


def load_bot_config(path: str | Path = "bot.yaml") -> BotConfig:
    config_path = Path(path)
    if not config_path.exists():
        return default_bot_config(name=config_path.parent.name or "my-copilot")
    raw = yaml.safe_load(config_path.read_text()) or {}
    return BotConfig.model_validate(raw)


def save_bot_config(config: BotConfig, path: str | Path = "bot.yaml") -> Path:
    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        yaml.safe_dump(config.model_dump(mode="json"), sort_keys=False),
        encoding="utf-8",
    )
    return config_path
