from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from ai_trading_framework.core.orchestration.pipeline import AnalysisPipeline
from ai_trading_framework.core.runtime.builder import FrameworkBuilder
from ai_trading_framework.core.runtime.settings import get_settings
from ai_trading_framework.data.providers.demo import (
    DemoFundamentalProvider,
    DemoMarketDataProvider,
    DemoNewsProvider,
    DemoSentimentProvider,
)
from ai_trading_framework.models import BrokerName
from ai_trading_framework.signals.finrl import FinRLSignalEngine
from ai_trading_framework.signals.technical import MomentumSignalEngine, MomentumStrategy


def create_app() -> FastAPI:
    settings = get_settings()
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

    app = FastAPI(title="AI Trading Framework", version="0.1.0")

    @app.get("/v1/health")
    async def health():
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        return """
        <html><body>
        <h1>AI Trading Framework</h1>
        <p>Telegram-first operator runtime with replayable approval-first workflows.</p>
        <ul>
        <li>Use <code>/v1/scan/{symbol}</code> to generate a recommendation</li>
        <li>Use <code>/v1/replay/{run_id}</code> to rebuild a previous run</li>
        </ul>
        </body></html>
        """

    @app.get("/v1/scan/{symbol}")
    async def scan(symbol: str, broker: BrokerName = BrokerName.PAPER):
        context, recommendations = await pipeline.analyze(symbol, broker=broker)
        run, recommendations, risks = await runtime.analyze(context, recommendations, broker=broker)
        return {
            "run_id": run.run_id,
            "recommendations": [item.model_dump(mode="json") for item in recommendations],
            "risks": [risk.model_dump(mode="json") for risk in risks],
        }

    @app.post("/v1/recommendations/{recommendation_id}/approve")
    async def approve(recommendation_id: str, token: str):
        try:
            approval = runtime.approval_service.approve(recommendation_id, token)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return approval.model_dump(mode="json")

    @app.get("/v1/replay/{run_id}")
    async def replay(run_id: str):
        replay_payload = runtime.replay(run_id)
        if not replay_payload:
            raise HTTPException(status_code=404, detail="Run not found.")
        return replay_payload

    @app.get("/v1/benchmark/{symbol}")
    async def benchmark(symbol: str):
        context, recommendations = await pipeline.analyze(symbol)
        _, recommendations, _ = await runtime.analyze(
            context, recommendations, broker=BrokerName.PAPER
        )
        return [
            item.model_dump(mode="json")
            for item in runtime.benchmark_service.compare(recommendations)
        ]

    return app
