from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from ai_trading_framework.core.orchestration.pipeline import AnalysisPipeline
from ai_trading_framework.core.runtime.builder import FrameworkBuilder
from ai_trading_framework.core.runtime.settings import get_settings
from ai_trading_framework.data.providers.demo import (
    DemoFundamentalProvider,
    DemoMarketDataProvider,
    DemoNewsProvider,
    DemoSentimentProvider,
)
from ai_trading_framework.models import BrokerName, OrderType
from ai_trading_framework.signals.finrl import FinRLSignalEngine
from ai_trading_framework.signals.technical import MomentumSignalEngine, MomentumStrategy


class OrderActionRequest(BaseModel):
    recommendation_id: str
    broker: BrokerName = BrokerName.PAPER
    quantity: int | None = None
    order_type: OrderType = OrderType.LIMIT
    approval_token: str | None = None
    limit_price: float | None = None
    stop_price: float | None = None


class TelegramWebhookPayload(BaseModel):
    update_id: int | None = None
    message: dict | None = None


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

    app = FastAPI(title="AI Trading Framework", version="0.2.0")

    def resolve_quantity(recommendation_id: str, requested: int | None) -> int:
        if requested:
            return requested
        risk = runtime.get_risk(recommendation_id)
        if risk and risk.max_position_size:
            return max(1, min(risk.max_position_size, 1))
        return 1

    @app.get("/v1/health")
    async def health():
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        return runtime.render_dashboard()

    @app.get("/v1/scan/{symbol}")
    async def scan(symbol: str, broker: BrokerName = BrokerName.PAPER):
        context, recommendations = await pipeline.analyze(symbol, broker=broker)
        run, recommendations, risks = await runtime.analyze(context, recommendations, broker=broker)
        return {
            "run_id": run.run_id,
            "recommendations": [item.model_dump(mode="json") for item in recommendations],
            "risks": [risk.model_dump(mode="json") for risk in risks],
        }

    @app.get("/v1/recommendations")
    async def list_recommendations():
        return runtime.list_recommendations()

    @app.get("/v1/recommendations/{identifier}")
    async def get_recommendation(identifier: str):
        recommendation = runtime.get_recommendation(identifier)
        if not recommendation:
            raise HTTPException(status_code=404, detail="Recommendation not found.")
        risk = runtime.get_risk(recommendation.recommendation_id)
        approval = runtime.get_approval(recommendation.recommendation_id)
        execution = runtime.executions.get(recommendation.recommendation_id)
        return {
            "recommendation": recommendation.model_dump(mode="json"),
            "risk": risk.model_dump(mode="json") if risk else None,
            "approval": approval.model_dump(mode="json") if approval else None,
            "execution": execution.model_dump(mode="json") if execution else None,
        }

    @app.post("/v1/recommendations/{recommendation_id}/approve")
    async def approve(recommendation_id: str, token: str):
        try:
            approval = await runtime.approve_recommendation(recommendation_id, token)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return approval.model_dump(mode="json")

    @app.post("/v1/recommendations/{recommendation_id}/reject")
    async def reject(recommendation_id: str, token: str):
        try:
            approval = await runtime.reject_recommendation(recommendation_id, token)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return approval.model_dump(mode="json")

    @app.post("/v1/orders/preview")
    async def preview_order(request: OrderActionRequest):
        quantity = resolve_quantity(request.recommendation_id, request.quantity)
        try:
            preview = await runtime.preview_order(
                recommendation_id=request.recommendation_id,
                broker=request.broker,
                quantity=quantity,
                order_type=request.order_type,
                limit_price=request.limit_price,
                stop_price=request.stop_price,
                approval_token=request.approval_token,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return preview.model_dump(mode="json")

    @app.post("/v1/orders/submit")
    async def submit_order(request: OrderActionRequest):
        quantity = resolve_quantity(request.recommendation_id, request.quantity)
        try:
            preview, result = await runtime.submit_order(
                recommendation_id=request.recommendation_id,
                broker=request.broker,
                quantity=quantity,
                order_type=request.order_type,
                approval_token=request.approval_token,
                limit_price=request.limit_price,
                stop_price=request.stop_price,
            )
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "preview": preview.model_dump(mode="json"),
            "result": result.model_dump(mode="json"),
        }

    @app.get("/v1/positions/{broker}")
    async def positions(broker: BrokerName):
        broker_positions = await runtime.get_positions(broker)
        return [position.model_dump(mode="json") for position in broker_positions]

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

    @app.post("/v1/telegram/webhook/{secret}")
    async def telegram_webhook(secret: str, payload: TelegramWebhookPayload):
        if secret != settings.telegram_webhook_secret:
            raise HTTPException(status_code=403, detail="Invalid Telegram webhook secret.")
        message = payload.message or {}
        text = str(message.get("text") or "").strip()
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id")) if chat.get("id") is not None else None
        parts = text.split()
        if parts and parts[0].lower() in {"/scan", "/analyze"} and len(parts) >= 2:
            symbol = parts[1].upper()
            context, recommendations = await pipeline.analyze(symbol, broker=BrokerName.PAPER)
            await runtime.analyze(context, recommendations, broker=BrokerName.PAPER)
        response = await runtime.handle_telegram_command(text, chat_id=chat_id)
        return {"ok": True, "response": response}

    return app
