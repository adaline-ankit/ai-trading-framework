from fastapi.testclient import TestClient

from ai_trading_framework.api.app import create_app
from ai_trading_framework.core.runtime.settings import get_settings


def test_api_paper_execution_and_telegram_webhook(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'framework.db'}")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "secret")
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
        assert submit.json()["result"]["status"] in {"PENDING", "REJECTED"}
