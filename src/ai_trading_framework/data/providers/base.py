from __future__ import annotations

from abc import ABC, abstractmethod

from ai_trading_framework.models import (
    Candle,
    FundamentalSnapshot,
    NewsArticle,
    PriceSnapshot,
    ProviderCapabilities,
    SentimentSnapshot,
)


class MarketDataProvider(ABC):
    capabilities = ProviderCapabilities(supports_intraday=True)

    @abstractmethod
    async def get_price(self, symbol: str) -> PriceSnapshot: ...

    @abstractmethod
    async def get_ohlc(self, symbol: str, lookback_days: int) -> list[Candle]: ...


class NewsProvider(ABC):
    capabilities = ProviderCapabilities(supports_news=True)

    @abstractmethod
    async def search(self, symbol: str, lookback_days: int) -> list[NewsArticle]: ...


class FundamentalProvider(ABC):
    capabilities = ProviderCapabilities(supports_fundamentals=True)

    @abstractmethod
    async def get_snapshot(self, symbol: str) -> FundamentalSnapshot: ...


class SentimentProvider(ABC):
    capabilities = ProviderCapabilities(supports_sentiment=True)

    @abstractmethod
    async def score(self, symbol: str, news: list[NewsArticle]) -> SentimentSnapshot: ...
