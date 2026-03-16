from fastapi.testclient import TestClient

from ai_trading_framework.api.app import create_app
from ai_trading_framework.core.runtime.settings import get_settings
from ai_trading_framework.models import (
    AssetClass,
    BrokerAuthSession,
    BrokerName,
    InstrumentDescriptor,
    Position,
    utcnow,
)


def test_api_paper_execution_and_telegram_webhook(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'framework.db'}")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "secret")
    monkeypatch.delenv("AUTH_MODE", raising=False)
    get_settings.cache_clear()
    app = create_app()

    with TestClient(app) as client:
        health = client.get("/v1/health")
        assert health.status_code == 200

        scan = client.get("/v1/scan/INFY?broker=PAPER")
        assert scan.status_code == 200
        run_id = scan.json()["run_id"]
        recommendation_id = scan.json()["recommendations"][0]["recommendation_id"]

        recommendations = client.get("/v1/recommendations")
        assert recommendations.status_code == 200
        assert len(recommendations.json()) >= 1

        detail = client.get(f"/v1/recommendations/{recommendation_id}")
        assert detail.status_code == 200
        assert detail.json()["approval"]["status"] == "PENDING"

        preview = client.post(
            "/v1/orders/preview",
            json={
                "recommendation_id": recommendation_id,
                "broker": "PAPER",
                "quantity": 2,
                "order_type": "LIMIT",
            },
        )
        assert preview.status_code == 200
        assert preview.json()["estimated_notional"] > 0

        submit = client.post(
            "/v1/orders/submit",
            json={
                "recommendation_id": recommendation_id,
                "broker": "PAPER",
                "quantity": 2,
                "order_type": "LIMIT",
            },
        )
        assert submit.status_code == 200
        assert submit.json()["result"]["status"] == "FILLED"

        positions = client.get("/v1/positions/PAPER")
        assert positions.status_code == 200
        assert positions.json()[0]["symbol"] == "INFY"

        why = client.post(
            "/v1/telegram/webhook/secret",
            json={"message": {"text": "/why INFY", "chat": {"id": 123}}},
        )
        assert why.status_code == 200
        assert "INFY" in why.json()["response"]

        replay = client.get(f"/v1/replay/{run_id}")
        assert replay.status_code == 200
        assert "ExecutionCompleted" in replay.json()


def test_telegram_callback_query_approval_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'framework.db'}")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "secret")
    monkeypatch.setenv("TELEGRAM_DEFAULT_CHAT_ID", "123")
    get_settings.cache_clear()
    app = create_app()
    runtime = app.state.runtime

    async def fake_answer(callback_query_id: str, text: str) -> None:
        return None

    async def fake_send_message(message: str, chat_id: str | None = None, **kwargs) -> None:
        return None

    monkeypatch.setattr(runtime.notifier, "answer_callback_query", fake_answer)
    monkeypatch.setattr(runtime.notifier, "send_message", fake_send_message)

    with TestClient(app) as client:
        scan = client.get("/v1/scan/INFY?broker=ZERODHA")
        assert scan.status_code == 200
        recommendation_id = scan.json()["recommendations"][0]["recommendation_id"]

        callback = client.post(
            "/v1/telegram/webhook/secret",
            json={
                "callback_query": {
                    "id": "callback-1",
                    "data": f"approve|{recommendation_id}",
                    "message": {"chat": {"id": 123}},
                }
            },
        )
        assert callback.status_code == 200
        assert "Approved" in callback.json()["response"]

        detail = client.get(f"/v1/recommendations/{recommendation_id}")
        assert detail.status_code == 200
        assert detail.json()["approval"]["status"] == "APPROVED"


def test_api_approval_before_live_submit(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'framework.db'}")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "secret")
    monkeypatch.delenv("AUTH_MODE", raising=False)
    get_settings.cache_clear()
    app = create_app()

    with TestClient(app) as client:
        scan = client.get("/v1/scan/TCS?broker=ZERODHA")
        assert scan.status_code == 200
        recommendation_id = scan.json()["recommendations"][0]["recommendation_id"]

        detail = client.get(f"/v1/recommendations/{recommendation_id}")
        approval_token = detail.json()["approval"]["token"]

        approve = client.post(
            f"/v1/recommendations/{recommendation_id}/approve",
            params={"token": approval_token},
        )
        assert approve.status_code == 200
        assert approve.json()["status"] == "APPROVED"

        submit = client.post(
            "/v1/orders/submit",
            json={
                "recommendation_id": recommendation_id,
                "broker": "ZERODHA",
                "quantity": 1,
                "order_type": "LIMIT",
                "approval_token": approval_token,
            },
        )
        assert submit.status_code == 200
        assert submit.json()["result"]["status"] in {"PENDING", "REJECTED", "FAILED"}


def test_password_auth_guards_operator_routes(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'framework.db'}")
    monkeypatch.setenv("AUTH_MODE", "PASSWORD")
    monkeypatch.setenv("ADMIN_EMAIL", "ops@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret-pass")
    monkeypatch.setenv("ADMIN_DISPLAY_NAME", "Ops")
    get_settings.cache_clear()
    app = create_app()

    with TestClient(app) as client:
        unauthenticated = client.get("/v1/recommendations")
        assert unauthenticated.status_code == 401

        providers = client.get("/v1/auth/providers")
        assert providers.status_code == 200
        assert providers.json()["password_enabled"] is True

        login = client.post(
            "/v1/auth/login",
            json={"email": "ops@example.com", "password": "secret-pass"},
        )
        assert login.status_code == 200
        assert login.json()["authenticated"] is True
        assert "password_hash" not in login.json()["operator"]

        me = client.get("/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["operator"]["email"] == "ops@example.com"
        assert "password_hash" not in me.json()["operator"]

        bootstrap = client.get("/v1/dashboard/bootstrap")
        assert bootstrap.status_code == 200
        assert "recommendations" in bootstrap.json()

        telegram_status = client.get("/v1/telegram/status")
        assert telegram_status.status_code == 200

        scan = client.get("/v1/scan/INFY?broker=PAPER")
        assert scan.status_code == 200

        clear = client.post("/v1/history/clear")
        assert clear.status_code == 200
        assert client.get("/v1/dashboard/bootstrap").json()["recommendations"] == []


def test_zerodha_callback_persists_broker_session(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'framework.db'}")
    monkeypatch.setenv("AUTH_MODE", "PASSWORD")
    monkeypatch.setenv("ADMIN_EMAIL", "ops@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret-pass")
    monkeypatch.setenv("ZERODHA_API_KEY", "kite-key")
    monkeypatch.setenv("ZERODHA_API_SECRET", "kite-secret")
    get_settings.cache_clear()
    app = create_app()
    runtime = app.state.runtime

    async def fake_exchange(request_token: str, actor_operator_id: str | None = None):
        session = BrokerAuthSession(
            broker=BrokerName.ZERODHA,
            request_token=request_token,
            access_token="access-token",
            public_token="public-token",
            api_key="kite-key",
            user_id="AB1234",
            user_name="Ankit",
            email="ankit@example.com",
            actor_operator_id=actor_operator_id,
            login_time="2026-03-16T00:00:00+00:00",
            received_at=utcnow(),
            raw={"request_token": request_token},
        )
        runtime.run_store.save_broker_session(session)
        runtime.get_zerodha_client().access_token = session.access_token
        return session

    monkeypatch.setattr(runtime.get_zerodha_client(), "exchange_request_token", fake_exchange)

    with TestClient(app) as client:
        login = client.post(
            "/v1/auth/login",
            json={"email": "ops@example.com", "password": "secret-pass"},
        )
        assert login.status_code == 200

        callback = client.get(
            "/v1/brokers/zerodha/callback?status=success&request_token=test-token",
            follow_redirects=False,
        )
        assert callback.status_code == 302

        status = client.get("/v1/brokers/zerodha")
        assert status.status_code == 200
        payload = status.json()
        assert payload["connected"] is True
        assert payload["session"]["user_id"] == "AB1234"

    reloaded_session = runtime.run_store.get_broker_session(BrokerName.ZERODHA)
    assert reloaded_session is not None
    assert reloaded_session.access_token == "access-token"


def test_multi_asset_zerodha_endpoints(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'framework.db'}")
    monkeypatch.delenv("AUTH_MODE", raising=False)
    get_settings.cache_clear()
    app = create_app()
    runtime = app.state.runtime

    async def fake_list_instruments(query=None, exchange=None, segment=None, limit=200):
        return [
            InstrumentDescriptor(
                broker=BrokerName.ZERODHA,
                symbol="NIFTY24MARFUT",
                tradingsymbol="NIFTY24MARFUT",
                exchange="NFO",
                segment="NFO-FUT",
                asset_class=AssetClass.FUTURE,
                instrument_type="FUTIDX",
            )
        ]

    async def fake_list_mutual_funds(query=None, limit=200):
        return [
            InstrumentDescriptor(
                broker=BrokerName.ZERODHA,
                symbol="INF179KC1HP0",
                tradingsymbol="INF179KC1HP0",
                name="Sample Index Fund",
                exchange="MF",
                segment="MF",
                asset_class=AssetClass.MUTUAL_FUND,
                instrument_type="MF",
            )
        ]

    async def fake_holdings():
        return [
            Position(
                symbol="NIFTYBEES",
                quantity=10.0,
                average_price=250.0,
                market_price=255.0,
                asset_class=AssetClass.ETF,
            )
        ]

    async def fake_mf_holdings():
        return [
            Position(
                symbol="INF179KC1HP0",
                quantity=12.345,
                average_price=42.0,
                market_price=43.5,
                asset_class=AssetClass.MUTUAL_FUND,
            )
        ]

    monkeypatch.setattr(runtime.get_zerodha_client(), "list_instruments", fake_list_instruments)
    monkeypatch.setattr(runtime.get_zerodha_client(), "list_mutual_funds", fake_list_mutual_funds)
    monkeypatch.setattr(runtime.get_zerodha_client(), "get_holdings", fake_holdings)
    monkeypatch.setattr(runtime.get_zerodha_client(), "get_mutual_fund_holdings", fake_mf_holdings)

    with TestClient(app) as client:
        capabilities = client.get("/v1/brokers/ZERODHA/capabilities")
        assert capabilities.status_code == 200
        assert capabilities.json()["supports_mutual_funds"] is True
        assert capabilities.json()["supports_futures"] is True

        instruments = client.get("/v1/brokers/zerodha/instruments?segment=NFO-FUT")
        assert instruments.status_code == 200
        assert instruments.json()[0]["asset_class"] == "FUTURE"

        funds = client.get("/v1/brokers/zerodha/mf/instruments")
        assert funds.status_code == 200
        assert funds.json()[0]["asset_class"] == "MUTUAL_FUND"

        holdings = client.get("/v1/brokers/zerodha/holdings")
        assert holdings.status_code == 200
        assert holdings.json()[0]["asset_class"] == "ETF"

        mf_holdings = client.get("/v1/brokers/zerodha/mf/holdings")
        assert mf_holdings.status_code == 200
        assert mf_holdings.json()[0]["quantity"] == 12.345


def test_hold_recommendation_cannot_execute(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'framework.db'}")
    monkeypatch.delenv("AUTH_MODE", raising=False)
    get_settings.cache_clear()
    app = create_app()

    with TestClient(app) as client:
        scan = client.get("/v1/scan/SBIN?broker=PAPER")
        assert scan.status_code == 200
        recommendation = scan.json()["recommendations"][0]
        assert recommendation["action"] == "HOLD"

        submit = client.post(
            "/v1/orders/submit",
            json={
                "recommendation_id": recommendation["recommendation_id"],
                "broker": "PAPER",
                "quantity": 1,
                "order_type": "LIMIT",
            },
        )
        assert submit.status_code == 200
        assert submit.json()["result"]["status"] == "REJECTED"
        assert "HOLD recommendations cannot be submitted" in submit.json()["result"]["message"]
