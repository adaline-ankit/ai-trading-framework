from __future__ import annotations

from ai_trading_framework.product.config import BotCapabilities


class HelpCapability:
    def __init__(self, capabilities: BotCapabilities) -> None:
        self.capabilities = capabilities

    def render(self) -> str:
        commands = [
            "/help",
            "/watchlist",
            "/watchlist add SYMBOL",
            "/watchlist remove SYMBOL",
            "/recommend [PAPER|ZERODHA] [SYMBOL...]",
            "/portfolio",
            "/positions",
            "/holdings",
            "/invest <amount|wallet> [SYMBOL...] [PAPER|ZERODHA]",
            "/why SYMBOL_OR_ID",
            "/risk SYMBOL_OR_ID",
            "/approve RECOMMENDATION_ID",
            "/reject RECOMMENDATION_ID",
            "/preview RECOMMENDATION_ID [PAPER|ZERODHA] [QTY]",
            "/submit RECOMMENDATION_ID [PAPER|ZERODHA] [QTY]",
            "/replay RUN_ID",
        ]
        enabled = [
            name
            for name, is_enabled in self.capabilities.model_dump(mode="json").items()
            if is_enabled
        ]
        return (
            "AI Trading Copilot commands\n"
            f"Enabled capabilities: {', '.join(enabled)}\n\n" + "\n".join(commands)
        )
