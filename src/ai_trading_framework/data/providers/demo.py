from __future__ import annotations

from datetime import timedelta

from ai_trading_framework.data.providers.base import (
    FundamentalProvider,
    MarketDataProvider,
    NewsProvider,
    SentimentProvider,
)
from ai_trading_framework.models import (
    Candle,
    FundamentalSnapshot,
    NewsArticle,
    PriceSnapshot,
    SentimentSnapshot,
    utcnow,
)


class DemoMarketDataProvider(MarketDataProvider):
    async def get_price(self, symbol: str) -> PriceSnapshot:
        seed = sum(ord(char) for char in symbol.upper())
        return PriceSnapshot(
            symbol=symbol.upper(),
            price=round(80 + (seed % 400) + 0.75, 2),
            change_percent=round(((seed % 13) - 6) / 10, 2),
            volume=250_000 + (seed % 150_000),
        )

    async def get_ohlc(self, symbol: str, lookback_days: int) -> list[Candle]:
        seed = sum(ord(char) for char in symbol.upper())
        base = 90 + (seed % 250)
        candles: list[Candle] = []
        start = utcnow() - timedelta(days=lookback_days)
        for index in range(lookback_days):
            drift = (index / max(lookback_days, 1)) * ((seed % 20) - 10)
            close = round(base + drift + ((index + seed) % 7) * 0.8, 2)
            candles.append(
                Candle(
                    timestamp=start + timedelta(days=index),
                    open=round(close - 0.6, 2),
                    high=round(close + 1.1, 2),
                    low=round(close - 1.3, 2),
                    close=close,
                    volume=180_000 + ((seed + index * 101) % 70_000),
                )
            )
        return candles


class DemoNewsProvider(NewsProvider):
    async def search(self, symbol: str, lookback_days: int) -> list[NewsArticle]:
        return [
            NewsArticle(
                symbol=symbol.upper(),
                headline=f"{symbol.upper()} demand remains resilient",
                summary="Analyst desks see stable trend strength and continued delivery momentum.",
                sentiment_score=0.25,
            ),
            NewsArticle(
                symbol=symbol.upper(),
                headline=f"{symbol.upper()} risk remains tied to macro softness",
                summary="Macro and sector rotation remain the main downside scenario.",
                sentiment_score=-0.05,
            ),
        ]


class DemoFundamentalProvider(FundamentalProvider):
    async def get_snapshot(self, symbol: str) -> FundamentalSnapshot:
        seed = sum(ord(char) for char in symbol.upper())
        return FundamentalSnapshot(
            symbol=symbol.upper(),
            sector="Technology" if seed % 2 else "Financials",
            market_cap=1_000_000_000 + (seed * 50_000),
            pe_ratio=18 + (seed % 12),
            eps=45 + (seed % 10),
            revenue_growth_percent=8 + (seed % 7),
            summary="Demo fundamentals indicate stable quality and moderate growth.",
        )


class DemoSentimentProvider(SentimentProvider):
    async def score(self, symbol: str, news: list[NewsArticle]) -> SentimentSnapshot:
        if not news:
            return SentimentSnapshot(
                symbol=symbol.upper(), score=0.0, label="neutral", summary="No news found."
            )
        score = round(sum(article.sentiment_score for article in news) / len(news), 4)
        label = "bullish" if score > 0.1 else "bearish" if score < -0.1 else "neutral"
        return SentimentSnapshot(
            symbol=symbol.upper(),
            score=score,
            label=label,
            summary=f"Average news sentiment is {label} ({score}).",
        )
