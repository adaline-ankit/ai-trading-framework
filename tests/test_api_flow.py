from fastapi.testclient import TestClient

from ai_trading_framework.api.app import create_app
from ai_trading_framework.core.runtime.settings import get_settings
from ai_trading_framework.models import BrokerAuthSession, BrokerName, utcnow


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

        scan = client.get("/v1/scan/INFY?broker=PAPER")
        assert scan.status_code == 200


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
