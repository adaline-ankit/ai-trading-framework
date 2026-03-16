from __future__ import annotations

from typing import Any, cast

from ai_trading_framework.analytics.investment_planner import InvestmentPlanner
from ai_trading_framework.core.orchestration.pipeline import AnalysisPipeline
from ai_trading_framework.core.runtime.operator import OperatorRuntime
from ai_trading_framework.models import BrokerName
from ai_trading_framework.product.capabilities import (
    PortfolioCapability,
    RecommendationCapability,
    WatchlistCapability,
)
from ai_trading_framework.product.config import BotConfig
from ai_trading_framework.product.state import WatchlistState


class ProductRouter:
    def __init__(
        self,
        *,
        config: BotConfig,
        runtime: OperatorRuntime,
        pipeline: AnalysisPipeline,
    ) -> None:
        self.config = config
        self.runtime = runtime
        self.pipeline = pipeline
        self.watchlist_state = WatchlistState(runtime.run_store, config.defaults.watchlist)
        self.watchlist = WatchlistCapability(self.watchlist_state)
        self.portfolio = PortfolioCapability(runtime)
        self.recommendations = RecommendationCapability(runtime, pipeline, self.watchlist_state)
        self.investment_planner = InvestmentPlanner(runtime, pipeline)

    async def handle_telegram(self, text: str, chat_id: str | None = None) -> str | None:
        parts = text.strip().split()
        if not parts:
            return "No command received."
        command = parts[0].lower()
        if command == "/watchlist":
            return await self._handle_watchlist(parts)
        if command == "/recommend":
            broker, symbols = self._extract_broker_and_symbols(parts[1:])
            payload = await self.recommendations.recommend(
                broker=broker,
                symbols=symbols or None,
                notify=True,
            )
            top = cast(dict[str, Any] | None, payload["top"])
            if not top:
                return "No recommendation available for the current watchlist."
            recommendation = cast(dict[str, Any], top["recommendation"])
            return (
                f"Top idea: {recommendation['symbol']} {recommendation['action']}\n"
                f"Confidence: {recommendation['confidence']:.0%}\n"
                f"Why: {recommendation['thesis']}"
            )
        if command in {"/portfolio", "/holdings"}:
            broker = self._extract_broker(parts[1:])
            summary = await self.portfolio.summary(broker)
            if command == "/holdings":
                items = cast(list[dict[str, Any]], summary["holdings"])
                label = "holdings"
            else:
                items = cast(list[dict[str, Any]], summary["positions"])
                label = "positions"
            if not items:
                return f"No {label} found for {broker.value}."
            lines = [
                (
                    f"{item['symbol']}: qty={item['quantity']} "
                    f"avg={item['average_price']} mark={item['market_price']}"
                )
                for item in items
            ]
            return "\n".join(lines)
        if text.lower().startswith("what should i buy") or text.lower().startswith("best idea"):
            payload = await self.recommendations.recommend(
                broker=self.config.broker,
                symbols=None,
                notify=True,
            )
            top = cast(dict[str, Any] | None, payload["top"])
            if not top:
                return "No recommendation available for the current watchlist."
            recommendation = cast(dict[str, Any], top["recommendation"])
            return (
                f"Top idea: {recommendation['symbol']} {recommendation['action']}\n"
                f"Confidence: {recommendation['confidence']:.0%}\n"
                f"Why: {recommendation['thesis']}"
            )
        if command == "/invest":
            return None
        return None

    async def _handle_watchlist(self, parts: list[str]) -> str:
        if len(parts) == 1 or parts[1].lower() == "list":
            items = self.watchlist.get_all()
            return "Watchlist: " + ", ".join(items) if items else "Watchlist is empty."
        if len(parts) >= 3 and parts[1].lower() == "add":
            items = self.watchlist.add(parts[2])
            return f"Added {parts[2].upper()}. Watchlist: {', '.join(items)}"
        if len(parts) >= 3 and parts[1].lower() == "remove":
            items = self.watchlist.remove(parts[2])
            return f"Removed {parts[2].upper()}. Watchlist: {', '.join(items)}"
        return "Usage: /watchlist [list|add SYMBOL|remove SYMBOL]"

    def _extract_broker(self, parts: list[str]) -> BrokerName:
        if parts and parts[-1].upper() in {"PAPER", "ZERODHA"}:
            return BrokerName(parts[-1].upper())
        return self.config.broker

    def _extract_broker_and_symbols(self, parts: list[str]) -> tuple[BrokerName, list[str]]:
        broker = self._extract_broker(parts)
        symbols = [part.upper() for part in parts if part.upper() not in {"PAPER", "ZERODHA"}]
        return broker, symbols
