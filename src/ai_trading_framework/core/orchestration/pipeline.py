from __future__ import annotations

from ai_trading_framework.core.plugin_system.interfaces import ReasoningEngine, SignalEngine
from ai_trading_framework.data.providers.base import (
    FundamentalProvider,
    MarketDataProvider,
    NewsProvider,
    SentimentProvider,
)
from ai_trading_framework.models import BrokerName, MarketContext, Recommendation
from ai_trading_framework.sdk.strategies.base import TradingStrategy


class AnalysisPipeline:
    def __init__(
        self,
        market_provider: MarketDataProvider,
        fundamental_provider: FundamentalProvider,
        news_provider: NewsProvider,
        sentiment_provider: SentimentProvider,
        strategy: TradingStrategy,
        signal_engines: list[SignalEngine],
        reasoning_engine: ReasoningEngine,
    ) -> None:
        self.market_provider = market_provider
        self.fundamental_provider = fundamental_provider
        self.news_provider = news_provider
        self.sentiment_provider = sentiment_provider
        self.strategy = strategy
        self.signal_engines = signal_engines
        self.reasoning_engine = reasoning_engine

    async def analyze(
        self, symbol: str, broker: BrokerName = BrokerName.PAPER, lookback_days: int = 60
    ) -> tuple[MarketContext, list[Recommendation]]:
        price = await self.market_provider.get_price(symbol)
        candles = await self.market_provider.get_ohlc(symbol, lookback_days)
        fundamentals = await self.fundamental_provider.get_snapshot(symbol)
        news = await self.news_provider.search(symbol, lookback_days)
        sentiment = await self.sentiment_provider.score(symbol, news)
        context = MarketContext(
            symbol=symbol.upper(),
            price=price,
            candles=candles,
            fundamentals=fundamentals,
            news=news,
            sentiment=sentiment,
            metadata={"broker": broker.value},
        )
        signals = await self.strategy.scan(context)
        evaluated = signals
        for engine in self.signal_engines:
            evaluated = await engine.evaluate(evaluated, context)
        recommendations: list[Recommendation] = []
        for item in evaluated:
            recommendations.append(await self.reasoning_engine.analyze(item, context))
        return context, recommendations
