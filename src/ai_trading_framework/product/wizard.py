from __future__ import annotations

from pathlib import Path

from ai_trading_framework.models import BrokerName
from ai_trading_framework.product.config import (
    BotConfig,
    available_templates,
    load_template_config,
)


def should_run_interactive_wizard(no_input: bool = False) -> bool:
    if no_input:
        return False
    try:
        import sys

        return sys.stdin.isatty()
    except Exception:
        return False


def build_wizard_config(
    *,
    name: str,
    template: str,
    broker: BrokerName,
    project_dir: Path,
) -> BotConfig:
    config = load_template_config(template)
    config.name = name
    config.broker = broker
    config.live_trading = broker != BrokerName.PAPER

    name_input = _prompt(f"Bot name [{name}]: ")
    if name_input:
        config.name = name_input

    template_choices = ", ".join(available_templates())
    template_input = _prompt(f"Template [{template}] ({template_choices}): ")
    if template_input and template_input in available_templates():
        config = load_template_config(template_input)
        config.name = name
        config.broker = broker
        config.live_trading = broker != BrokerName.PAPER

    broker_input = _prompt(f"Broker [{config.broker.value}] (PAPER/ZERODHA): ").upper()
    if broker_input in {"PAPER", "ZERODHA"}:
        config.broker = BrokerName(broker_input)
        config.live_trading = config.broker != BrokerName.PAPER

    telegram_enabled = _prompt_yes_no(
        f"Enable Telegram [{_yes_no_label(config.telegram.enabled)}]: ",
        default=config.telegram.enabled,
    )
    config.telegram.enabled = telegram_enabled

    auto_budget = _prompt_yes_no(
        f"Use broker funds automatically when available "
        f"[{_yes_no_label(config.broker_settings.auto_budget_mode)}]: ",
        default=config.broker_settings.auto_budget_mode,
    )
    config.broker_settings.auto_budget_mode = auto_budget
    config.broker_settings.funds_source = "broker" if auto_budget else "manual"

    watchlist_input = _prompt(f"Default watchlist [{','.join(config.defaults.watchlist)}]: ")
    if watchlist_input:
        parsed_watchlist = _parse_symbol_list(watchlist_input)
        if parsed_watchlist:
            config.defaults.watchlist = parsed_watchlist
            config.defaults.recommendation_universe = parsed_watchlist

    budget_input = _prompt(f"Default budget [{config.defaults.default_budget}]: ")
    if budget_input:
        try:
            config.defaults.default_budget = float(budget_input)
        except ValueError:
            pass

    live_input = _prompt_yes_no(
        f"Enable live trading [{_yes_no_label(config.live_trading)}]: ",
        default=config.live_trading,
    )
    config.live_trading = live_input
    if not live_input:
        config.broker = BrokerName.PAPER

    config.risk.max_capital_per_trade = config.defaults.default_budget
    config.strategy.custom_strategy_module = str(project_dir / "strategies")
    return config


def _prompt(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        return ""


def _prompt_yes_no(prompt: str, *, default: bool) -> bool:
    raw = _prompt(prompt).lower()
    if not raw:
        return default
    if raw in {"y", "yes"}:
        return True
    if raw in {"n", "no"}:
        return False
    return default


def _yes_no_label(value: bool) -> str:
    return "Y/n" if value else "y/N"


def _parse_symbol_list(raw: str) -> list[str]:
    return [item.strip().upper() for item in raw.replace(" ", ",").split(",") if item.strip()]
