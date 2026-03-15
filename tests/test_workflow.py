import pytest

from ai_trading_framework.core.orchestration import AnalysisPipeline
from ai_trading_framework.core.runtime.builder import FrameworkBuilder
from ai_trading_framework.core.runtime.settings import Settings
from ai_trading_framework.data.providers.demo import (
    DemoFundamentalProvider,
    DemoMarketDataProvider,
    DemoNewsProvider,
    DemoSentimentProvider,
)
from ai_trading_framework.models import BrokerName
from ai_trading_framework.signals.finrl import FinRLSignalEngine
from ai_trading_framework.signals.technical import MomentumSignalEngine, MomentumStrategy


@pytest.mark.asyncio
async def test_flagship_workflow_and_replay(tmp_path):
    settings = Settings(DATABASE_URL=f"sqlite:///{tmp_path / 'framework.db'}")
    builder = FrameworkBuilder(settings)
    runtime = builder.build()
    pipeline = AnalysisPipeline(
        market_provider=DemoMarketDataProvider(),
        fundamental_provider=DemoFundamentalProvider(),
        news_provider=DemoNewsProvider(),
        sentiment_provider=DemoSentimentProvider(),
        strategy=MomentumStrategy(),
        signal_engines=[MomentumSignalEngine(), FinRLSignalEngine()],
        reasoning_engine=builder.reasoning_engine,
    )
    context, recommendations = await pipeline.analyze("INFY", broker=BrokerName.ZERODHA)
    run, recommendations, risks = await runtime.analyze(
        context, recommendations, broker=BrokerName.ZERODHA, simulate_approval=True
    )
    assert recommendations
    assert risks[0].decision.value in {"APPROVED", "REVIEW", "REJECTED"}
    replay = runtime.replay(run.run_id)
    assert replay is not None
    assert "RecommendationCreated" in replay
