import json
import sys

from fastapi.testclient import TestClient

from ai_trading_framework.api.app import create_app
from ai_trading_framework.core.cli.main import main
from ai_trading_framework.core.runtime.settings import get_settings


def test_dashboard_and_telegram_management_routes(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'framework.db'}")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.com")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "secret")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot-token")
    monkeypatch.setenv("TELEGRAM_DEFAULT_CHAT_ID", "123")
    monkeypatch.delenv("AUTH_MODE", raising=False)
    get_settings.cache_clear()
    app = create_app()
    runtime = app.state.runtime

    async def fake_get_webhook_info():
        return {"ok": True, "result": {"url": "https://example.com/hook"}}

    async def fake_set_webhook(url: str, secret_token: str | None = None):
        return {"ok": True, "result": True, "url": url, "secret_token": secret_token}

    monkeypatch.setattr(runtime.notifier, "get_webhook_info", fake_get_webhook_info)
    monkeypatch.setattr(runtime.notifier, "set_webhook", fake_set_webhook)

    with TestClient(app) as client:
        dashboard = client.get("/")
        assert dashboard.status_code == 200
        assert "Run Scan" in dashboard.text
        assert "Connect Zerodha" in dashboard.text

        status = client.get("/v1/telegram/status")
        assert status.status_code == 200
        assert status.json()["enabled"] is True
        assert status.json()["webhook"]["ok"] is True

        setup = client.post("/v1/telegram/setup")
        assert setup.status_code == 200
        assert setup.json()["webhook_url"] == "https://example.com/v1/telegram/webhook/secret"


def test_investment_plan_api_and_telegram_command(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'framework.db'}")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "secret")
    monkeypatch.setenv("TELEGRAM_DEFAULT_CHAT_ID", "123")
    get_settings.cache_clear()
    app = create_app()
    runtime = app.state.runtime
    sent_messages: list[str] = []
    sent_recommendations: list[str] = []

    async def fake_send_message(message: str, chat_id: str | None = None, **kwargs) -> None:
        sent_messages.append(message)

    async def fake_send_recommendation(
        recommendation,
        approval_token: str | None = None,
        chat_id=None,
    ):
        sent_recommendations.append(f"{recommendation.symbol}:{approval_token}")

    monkeypatch.setattr(runtime.notifier, "send_message", fake_send_message)
    monkeypatch.setattr(runtime.notifier, "send_recommendation", fake_send_recommendation)

    with TestClient(app) as client:
        plan = client.post(
            "/v1/investment-plan",
            json={"budget": 10000, "symbols": ["INFY", "TCS", "SBIN"], "broker": "PAPER"},
        )
        assert plan.status_code == 200
        payload = plan.json()
        assert payload["selected"] is not None
        assert payload["selected"]["action"] == "BUY"
        assert payload["selected"]["suggested_quantity"] >= 1
        assert payload["recommendation"]["symbol"] == payload["selected"]["symbol"]
        assert payload["approval"]["status"] == "PENDING"

        webhook = client.post(
            "/v1/telegram/webhook/secret",
            json={"message": {"text": "/invest 10000 INFY TCS SBIN PAPER", "chat": {"id": 123}}},
        )
        assert webhook.status_code == 200
        assert "Best idea:" in webhook.json()["response"]
        assert sent_recommendations
        assert sent_messages


def test_cli_scan_benchmark_and_invest_commands(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'framework.db'}")
    get_settings.cache_clear()

    monkeypatch.setattr(sys, "argv", ["ai-trading", "scan", "INFY"])
    main()
    scan_output = json.loads(capsys.readouterr().out)
    assert scan_output["recommendations"]

    monkeypatch.setattr(sys, "argv", ["ai-trading", "benchmark", "INFY"])
    main()
    benchmark_output = json.loads(capsys.readouterr().out)
    assert benchmark_output[0]["strategy_name"]

    monkeypatch.setattr(
        sys,
        "argv",
        ["ai-trading", "invest", "10000", "INFY", "TCS", "SBIN", "--broker", "PAPER"],
    )
    main()
    invest_output = json.loads(capsys.readouterr().out)
    assert invest_output["selected"] is not None
    assert invest_output["selected"]["estimated_notional"] <= 10000


def test_cli_init_doctor_status_and_watchlist_commands(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'framework.db'}")
    get_settings.cache_clear()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ai-trading",
            "init",
            "alpha-bot",
            "--template",
            "paper-sandbox",
            "--path",
            str(tmp_path),
        ],
    )
    main()
    init_output = capsys.readouterr().out
    project_dir = tmp_path / "alpha-bot"
    assert "Initialized bot project" in init_output
    assert project_dir.exists()
    assert (project_dir / "bot.yaml").exists()
    assert (project_dir / ".env.example").exists()
    assert (project_dir / "README.md").exists()
    assert (project_dir / "strategies" / ".gitkeep").exists()

    monkeypatch.chdir(project_dir)
    monkeypatch.setenv("BOT_CONFIG_PATH", "bot.yaml")
    get_settings.cache_clear()

    monkeypatch.setattr(sys, "argv", ["ai-trading", "doctor"])
    main()
    doctor_output = json.loads(capsys.readouterr().out)
    assert doctor_output["config_exists"] is True
    assert doctor_output["bot_name"] == "alpha-bot"
    assert doctor_output["broker"] == "PAPER"

    monkeypatch.setattr(sys, "argv", ["ai-trading", "watchlist", "add", "ITC"])
    main()
    watchlist_add_output = json.loads(capsys.readouterr().out)
    assert "ITC" in watchlist_add_output["items"]

    monkeypatch.setattr(sys, "argv", ["ai-trading", "status"])
    main()
    status_output = json.loads(capsys.readouterr().out)
    assert status_output["bot_name"] == "alpha-bot"
    assert "ITC" in status_output["watchlist"]


def test_unified_watchlist_and_recommendation_routes(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'framework.db'}")
    bot_config = tmp_path / "bot.yaml"
    bot_config.write_text(
        "\n".join(
            [
                "name: route-bot",
                "broker: PAPER",
                "defaults:",
                "  watchlist:",
                "    - INFY",
                "    - TCS",
                "  recommendation_universe:",
                "    - INFY",
                "    - TCS",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("BOT_CONFIG_PATH", str(bot_config))
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "secret")
    monkeypatch.setenv("TELEGRAM_DEFAULT_CHAT_ID", "123")
    get_settings.cache_clear()
    app = create_app()
    runtime = app.state.runtime
    sent_messages: list[str] = []

    async def fake_send_message(message: str, chat_id: str | None = None, **kwargs) -> None:
        sent_messages.append(message)

    monkeypatch.setattr(runtime.notifier, "send_message", fake_send_message)

    with TestClient(app) as client:
        watchlist = client.get("/v1/watchlist")
        assert watchlist.status_code == 200
        assert watchlist.json()["items"] == ["INFY", "TCS"]

        add = client.post("/v1/watchlist/SBIN")
        assert add.status_code == 200
        assert "SBIN" in add.json()["items"]

        recommend = client.get("/v1/recommend?symbols=INFY,TCS")
        assert recommend.status_code == 200
        payload = recommend.json()
        assert payload["count"] >= 1
        assert payload["top"] is not None
        assert payload["top"]["recommendation"]["symbol"] in {"INFY", "TCS"}

        telegram_watchlist = client.post(
            "/v1/telegram/webhook/secret",
            json={"message": {"text": "/watchlist add HDFCBANK", "chat": {"id": 123}}},
        )
        assert telegram_watchlist.status_code == 200
        assert "Added HDFCBANK" in telegram_watchlist.json()["response"]

        telegram_recommend = client.post(
            "/v1/telegram/webhook/secret",
            json={"message": {"text": "/recommend PAPER INFY TCS", "chat": {"id": 123}}},
        )
        assert telegram_recommend.status_code == 200
        assert "Top idea:" in telegram_recommend.json()["response"]
        assert sent_messages
