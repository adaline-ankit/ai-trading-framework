from __future__ import annotations

from urllib.parse import quote_plus

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from ai_trading_framework.api.dashboard import render_operator_console
from ai_trading_framework.core.orchestration.pipeline import AnalysisPipeline
from ai_trading_framework.core.runtime.builder import FrameworkBuilder
from ai_trading_framework.core.runtime.settings import get_settings
from ai_trading_framework.core.security.auth import OperatorAuthError
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
    callback_query: dict | None = None


class PasswordLoginRequest(BaseModel):
    email: str
    password: str


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

    app = FastAPI(title="AI Trading Framework", version="0.3.0")
    app.state.runtime = runtime
    app.state.pipeline = pipeline

    def current_operator(request: Request):
        auth_service = runtime.auth_service
        if not auth_service or not auth_service.is_enabled():
            return None
        token = request.cookies.get(settings.session_cookie_name)
        return auth_service.get_operator_for_session_token(token)

    def require_operator(request: Request):
        operator = current_operator(request)
        if runtime.auth_service and runtime.auth_service.is_enabled() and not operator:
            raise HTTPException(status_code=401, detail="Operator authentication is required.")
        return operator

    def set_session_cookie(response: JSONResponse | RedirectResponse, session_token: str) -> None:
        response.set_cookie(
            key=settings.session_cookie_name,
            value=session_token,
            httponly=True,
            secure=settings.app_env.lower() == "prod",
            samesite="lax",
            max_age=settings.session_ttl_hours * 3600,
        )

    def clear_session_cookie(response: JSONResponse | RedirectResponse) -> None:
        response.delete_cookie(settings.session_cookie_name)

    def zerodha_public_session() -> dict[str, object] | None:
        session = runtime.get_zerodha_client().current_session()
        if not session:
            return None
        return {
            "broker": session.broker.value,
            "user_id": session.user_id,
            "user_name": session.user_name,
            "email": session.email,
            "login_time": session.login_time,
            "actor_operator_id": session.actor_operator_id,
            "received_at": session.received_at.isoformat(),
        }

    def operator_public_payload(operator) -> dict[str, object]:
        return {
            "operator_id": operator.operator_id,
            "email": operator.email,
            "display_name": operator.display_name,
            "role": operator.role.value,
            "auth_provider": operator.auth_provider,
            "provider_subject": operator.provider_subject,
            "metadata": operator.metadata,
            "created_at": operator.created_at.isoformat(),
            "last_login_at": operator.last_login_at.isoformat() if operator.last_login_at else None,
        }

    def render_login_page(error: str | None = None) -> HTMLResponse:
        auth_service = runtime.auth_service
        auth_summary = auth_service.auth_summary() if auth_service else {"enabled": False}
        error_block = (
            "<p style='color:#b42318;background:#fee4e2;padding:12px;border-radius:10px;'>"
            f"{error}</p>"
            if error
            else ""
        )
        password_form = ""
        if auth_summary.get("password_enabled"):
            password_form = (
                "<form method='post' action='/v1/auth/login' style='display:grid;gap:12px;'>"
                "<input type='email' name='email' placeholder='Operator email' "
                "style='padding:10px;border:1px solid #d0d5dd;border-radius:8px;' required />"
                "<input type='password' name='password' placeholder='Password' "
                "style='padding:10px;border:1px solid #d0d5dd;border-radius:8px;' required />"
                "<button type='submit' style='padding:10px 14px;border-radius:8px;"
                "border:none;background:#111827;color:white;'>Sign In</button>"
                "</form>"
            )
        oidc_button = ""
        if auth_summary.get("oidc_enabled"):
            provider = str(auth_summary.get("oidc_provider") or "OIDC")
            oidc_button = (
                f"<a href='/v1/auth/login/{provider}' "
                "style='display:inline-block;padding:10px 14px;border-radius:8px;"
                "background:#0f766e;color:white;text-decoration:none;'>"
                f"Continue with {provider.title()}</a>"
            )
        return HTMLResponse(
            "<html><body style='font-family:system-ui;background:#f8fafc;margin:0;'>"
            "<main style='max-width:460px;margin:56px auto;padding:24px;'>"
            "<section style='background:white;padding:24px;border-radius:18px;"
            "box-shadow:0 18px 60px rgba(15,23,42,0.12);'>"
            "<h1 style='margin-top:0;'>AI Trading Framework</h1>"
            "<p>Operator access is protected. Sign in to review recommendations, "
            "approve trades, and manage broker connectivity.</p>"
            f"{error_block}{password_form}"
            f"<div style='margin-top:16px;'>{oidc_button}</div>"
            "</section></main></body></html>",
            status_code=401,
        )

    def resolve_quantity(recommendation_id: str, requested: int | None) -> int:
        if requested:
            return requested
        risk = runtime.get_risk(recommendation_id)
        if risk and risk.max_position_size:
            return max(1, min(risk.max_position_size, 1))
        return 1

    def telegram_status_payload() -> dict[str, object]:
        notifier = runtime.notifier
        if not notifier:
            return {"enabled": False, "configured": False}
        return {
            "enabled": getattr(notifier, "enabled", False),
            "configured": bool(settings.telegram_bot_token and settings.telegram_default_chat_id),
            "default_chat_id": settings.telegram_default_chat_id,
        }

    def ensure_allowed_telegram_chat(chat_id: str | None) -> None:
        expected = settings.telegram_default_chat_id
        if expected and chat_id and chat_id != expected:
            raise HTTPException(status_code=403, detail="Telegram chat is not authorized.")

    protected_operator = Depends(require_operator)

    @app.get("/v1/health")
    async def health():
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        operator = current_operator(request)
        if runtime.auth_service and runtime.auth_service.is_enabled() and not operator:
            return render_login_page(request.query_params.get("error"))
        return HTMLResponse(
            render_operator_console(
                settings.app_name,
                operator_public_payload(operator) if operator else None,
            )
        )

    @app.get("/v1/auth/providers")
    async def auth_providers():
        auth_service = runtime.auth_service
        if auth_service:
            return auth_service.auth_summary()
        return {"enabled": False, "mode": "DISABLED"}

    @app.get("/v1/auth/me")
    async def auth_me(request: Request):
        operator = current_operator(request)
        auth_service = runtime.auth_service
        return {
            "auth": auth_service.auth_summary() if auth_service else {"enabled": False},
            "operator": operator_public_payload(operator) if operator else None,
        }

    @app.get("/v1/dashboard/bootstrap")
    async def dashboard_bootstrap(_operator=protected_operator):
        zerodha_status = {
            "connected": runtime.get_zerodha_client().is_connected(),
            "login_url": runtime.get_zerodha_client().login_url(),
            "session": zerodha_public_session(),
        }
        zerodha_positions = []
        if zerodha_status["connected"]:
            zerodha_positions = [
                position.model_dump(mode="json")
                for position in await runtime.get_positions(BrokerName.ZERODHA)
            ]
        return {
            "recommendations": runtime.list_recommendations(),
            "zerodha": zerodha_status,
            "telegram": telegram_status_payload(),
            "positions": {
                "paper": [
                    position.model_dump(mode="json")
                    for position in await runtime.get_positions(BrokerName.PAPER)
                ],
                "zerodha": zerodha_positions,
            },
        }

    @app.post("/v1/auth/login")
    async def auth_login(request: Request):
        auth_service = runtime.auth_service
        if not auth_service:
            raise HTTPException(status_code=400, detail="Authentication is not configured.")
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            payload = PasswordLoginRequest.model_validate(await request.json())
        else:
            form = await request.form()
            payload = PasswordLoginRequest(
                email=str(form.get("email") or ""),
                password=str(form.get("password") or ""),
            )
        try:
            operator_session = auth_service.authenticate_password(payload.email, payload.password)
        except OperatorAuthError as exc:
            if "application/json" in content_type:
                raise HTTPException(status_code=401, detail=str(exc)) from exc
            return render_login_page(str(exc))
        operator = auth_service.get_operator_for_session_token(operator_session.session_token)
        if not operator:
            raise HTTPException(
                status_code=500,
                detail="Authenticated operator session was not created.",
            )
        response = JSONResponse(
            {
                "authenticated": True,
                "operator": operator_public_payload(operator),
            }
        )
        set_session_cookie(response, operator_session.session_token)
        if "application/json" not in content_type:
            redirect = RedirectResponse(url="/", status_code=303)
            set_session_cookie(redirect, operator_session.session_token)
            return redirect
        return response

    @app.get("/v1/auth/login/{provider}")
    async def auth_login_provider(provider: str, redirect_after: str | None = None):
        auth_service = runtime.auth_service
        if not auth_service or not auth_service.supports_oidc():
            raise HTTPException(status_code=400, detail="OIDC is not configured.")
        oidc_provider = auth_service.oidc_provider()
        if not oidc_provider or provider != oidc_provider.name:
            raise HTTPException(status_code=404, detail="Unknown OIDC provider.")
        try:
            login_url = await auth_service.begin_oidc_login(redirect_after=redirect_after)
        except OperatorAuthError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return RedirectResponse(url=login_url, status_code=302)

    @app.get("/v1/auth/callback/{provider}")
    async def auth_callback(provider: str, code: str | None = None, state: str | None = None):
        auth_service = runtime.auth_service
        if not auth_service or not auth_service.supports_oidc():
            raise HTTPException(status_code=400, detail="OIDC is not configured.")
        oidc_provider = auth_service.oidc_provider()
        if not oidc_provider or provider != oidc_provider.name:
            raise HTTPException(status_code=404, detail="Unknown OIDC provider.")
        if not code or not state:
            raise HTTPException(status_code=400, detail="OIDC callback is missing code or state.")
        try:
            operator_session, redirect_after = await auth_service.complete_oidc_login(code, state)
        except OperatorAuthError as exc:
            return RedirectResponse(
                url=f"/?error={quote_plus(str(exc))}",
                status_code=302,
            )
        response = RedirectResponse(url=redirect_after, status_code=302)
        set_session_cookie(response, operator_session.session_token)
        return response

    @app.post("/v1/auth/logout")
    async def auth_logout(request: Request):
        auth_service = runtime.auth_service
        if auth_service:
            auth_service.logout(request.cookies.get(settings.session_cookie_name))
        response = JSONResponse({"authenticated": False})
        clear_session_cookie(response)
        return response

    @app.post("/v1/history/clear")
    async def clear_history(_operator=protected_operator):
        runtime.clear_history()
        return {"ok": True}

    @app.get("/v1/telegram/status")
    async def telegram_status(_operator=protected_operator):
        notifier = runtime.notifier
        payload = telegram_status_payload()
        if notifier and getattr(notifier, "enabled", False):
            payload["webhook"] = await notifier.get_webhook_info()
        return payload

    @app.post("/v1/telegram/setup")
    async def telegram_setup(_operator=protected_operator):
        notifier = runtime.notifier
        if not notifier or not getattr(notifier, "bot_token", None):
            raise HTTPException(status_code=400, detail="Telegram bot token is not configured.")
        webhook_url = (
            f"{settings.public_base_url.rstrip('/')}/v1/telegram/webhook/"
            f"{settings.telegram_webhook_secret}"
        )
        payload = await notifier.set_webhook(webhook_url)
        return {
            "webhook_url": webhook_url,
            "result": payload,
        }

    @app.get("/v1/scan/{symbol}")
    async def scan(
        symbol: str,
        broker: BrokerName = BrokerName.PAPER,
        _operator=protected_operator,
    ):
        context, recommendations = await pipeline.analyze(symbol, broker=broker)
        run, recommendations, risks = await runtime.analyze(context, recommendations, broker=broker)
        return {
            "run_id": run.run_id,
            "recommendations": [item.model_dump(mode="json") for item in recommendations],
            "risks": [risk.model_dump(mode="json") for risk in risks],
        }

    @app.get("/v1/recommendations")
    async def list_recommendations(_operator=protected_operator):
        return runtime.list_recommendations()

    @app.get("/v1/recommendations/{identifier}")
    async def get_recommendation(identifier: str, _operator=protected_operator):
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
    async def approve(recommendation_id: str, token: str, _operator=protected_operator):
        try:
            approval = await runtime.approve_recommendation(recommendation_id, token)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return approval.model_dump(mode="json")

    @app.post("/v1/recommendations/{recommendation_id}/reject")
    async def reject(recommendation_id: str, token: str, _operator=protected_operator):
        try:
            approval = await runtime.reject_recommendation(recommendation_id, token)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return approval.model_dump(mode="json")

    @app.post("/v1/orders/preview")
    async def preview_order(request: OrderActionRequest, _operator=protected_operator):
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
    async def submit_order(request: OrderActionRequest, _operator=protected_operator):
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
    async def positions(broker: BrokerName, _operator=protected_operator):
        broker_positions = await runtime.get_positions(broker)
        return [position.model_dump(mode="json") for position in broker_positions]

    @app.get("/v1/replay/{run_id}")
    async def replay(run_id: str, _operator=protected_operator):
        replay_payload = runtime.replay(run_id)
        if not replay_payload:
            raise HTTPException(status_code=404, detail="Run not found.")
        return replay_payload

    @app.get("/v1/benchmark/{symbol}")
    async def benchmark(symbol: str, _operator=protected_operator):
        context, recommendations = await pipeline.analyze(symbol)
        _, recommendations, _ = await runtime.analyze(
            context, recommendations, broker=BrokerName.PAPER
        )
        return [
            item.model_dump(mode="json")
            for item in runtime.benchmark_service.compare(recommendations)
        ]

    @app.get("/v1/brokers/zerodha")
    async def zerodha_status(_operator=protected_operator):
        client = runtime.get_zerodha_client()
        return {
            "connected": client.is_connected(),
            "login_url": client.login_url(),
            "session": zerodha_public_session(),
        }

    @app.get("/v1/brokers/zerodha/login")
    async def zerodha_login(_operator=protected_operator):
        client = runtime.get_zerodha_client()
        login_url = client.login_url()
        if not login_url:
            raise HTTPException(status_code=400, detail="Zerodha is not configured.")
        return RedirectResponse(url=login_url, status_code=302)

    @app.get("/v1/brokers/zerodha/callback")
    async def zerodha_callback(request: Request):
        operator = current_operator(request)
        client = runtime.get_zerodha_client()
        status_value = request.query_params.get("status", "success")
        request_token = request.query_params.get("request_token")
        if status_value != "success" or not request_token:
            return RedirectResponse(
                url="/?error=Zerodha+login+did+not+return+a+valid+request+token",
                status_code=302,
            )
        try:
            await client.exchange_request_token(
                request_token, actor_operator_id=operator.operator_id if operator else None
            )
        except Exception as exc:  # pragma: no cover - external API failure branch
            return RedirectResponse(
                url=f"/?error={quote_plus(str(exc))}",
                status_code=302,
            )
        return RedirectResponse(url="/", status_code=302)

    @app.post("/v1/brokers/zerodha/disconnect")
    async def zerodha_disconnect(_operator=protected_operator):
        runtime.get_zerodha_client().disconnect()
        return {"connected": False}

    @app.post("/v1/telegram/webhook/{secret}")
    async def telegram_webhook(secret: str, payload: TelegramWebhookPayload):
        if secret != settings.telegram_webhook_secret:
            raise HTTPException(status_code=403, detail="Invalid Telegram webhook secret.")
        callback_query = payload.callback_query or {}
        if callback_query:
            chat = (callback_query.get("message") or {}).get("chat") or {}
            chat_id = str(chat.get("id")) if chat.get("id") is not None else None
            ensure_allowed_telegram_chat(chat_id)
            data = str(callback_query.get("data") or "")
            action, _, recommendation_id = data.partition("|")
            if not recommendation_id:
                raise HTTPException(
                    status_code=400,
                    detail="Telegram callback is missing a recommendation id.",
                )
            if action == "approve":
                approval = await runtime.approve_with_stored_token(recommendation_id)
                response = f"Approved {approval.recommendation_id}."
            elif action == "reject":
                approval = await runtime.reject_with_stored_token(recommendation_id)
                response = f"Rejected {approval.recommendation_id}."
            elif action == "why":
                recommendation = runtime.get_recommendation(recommendation_id)
                if recommendation:
                    response = recommendation.explain().why_this_trade
                else:
                    response = "Recommendation not found."
            elif action == "risk":
                recommendation = runtime.get_recommendation(recommendation_id)
                if not recommendation:
                    response = "Recommendation not found."
                else:
                    risk = runtime.get_risk(recommendation.recommendation_id)
                    if not risk:
                        response = "Risk evaluation not found."
                    else:
                        reasons = [reason for check in risk.checks for reason in check.reasons]
                        response = "\n".join([f"{risk.decision}: {risk.summary}", *reasons])
            else:
                response = "Unsupported Telegram action."
            notifier = runtime.notifier
            if notifier and callback_query.get("id"):
                await notifier.answer_callback_query(str(callback_query["id"]), response[:180])
            if notifier and chat_id:
                await notifier.send_message(response, chat_id=chat_id)
            return {"ok": True, "response": response}

        message = payload.message or {}
        text = str(message.get("text") or "").strip()
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id")) if chat.get("id") is not None else None
        ensure_allowed_telegram_chat(chat_id)
        parts = text.split()
        if parts and parts[0].lower() in {"/scan", "/analyze"} and len(parts) >= 2:
            symbol = parts[1].upper()
            broker = BrokerName.PAPER
            if len(parts) >= 3 and parts[2].upper() in {"PAPER", "ZERODHA"}:
                broker = BrokerName(parts[2].upper())
            context, recommendations = await pipeline.analyze(symbol, broker=broker)
            await runtime.analyze(context, recommendations, broker=broker)
        response = await runtime.handle_telegram_command(text, chat_id=chat_id)
        return {"ok": True, "response": response}

    return app
