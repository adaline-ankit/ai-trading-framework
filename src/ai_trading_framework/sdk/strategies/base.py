from __future__ import annotations

from abc import ABC, abstractmethod

from ai_trading_framework.models import MarketContext, Recommendation, Signal


class TradingStrategy(ABC):
    name = "strategy"
    supported_markets: list[str] = ["NSE"]
    symbols: list[str] = []
    tags: list[str] = []
    default_risk_profile: str = "balanced"

    @abstractmethod
    async def scan(self, market_context: MarketContext) -> list[Signal]: ...

    @abstractmethod
    async def analyze(self, signal: Signal, context: MarketContext) -> Recommendation | None: ...
