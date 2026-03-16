from __future__ import annotations

import argparse
import asyncio
import json
import os
import webbrowser
from pathlib import Path

import uvicorn

from ai_trading_framework import __version__
from ai_trading_framework.analytics import BenchmarkService, InvestmentPlanner
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
from ai_trading_framework.product.config import (
    BotConfig,
    available_templates,
    default_bot_config,
    load_bot_config,
    load_template_config,
    save_bot_config,
)
from ai_trading_framework.product.router import ProductRouter
from ai_trading_framework.product.state import WatchlistState
from ai_trading_framework.product.wizard import build_wizard_config, should_run_interactive_wizard
from ai_trading_framework.signals.finrl import FinRLSignalEngine
from ai_trading_framework.signals.technical import MomentumSignalEngine, MomentumStrategy


def build_pipeline(builder: FrameworkBuilder) -> AnalysisPipeline:
    return AnalysisPipeline(
        market_provider=DemoMarketDataProvider(),
        fundamental_provider=DemoFundamentalProvider(),
        news_provider=DemoNewsProvider(),
        sentiment_provider=DemoSentimentProvider(),
        strategy=MomentumStrategy(),
        signal_engines=[MomentumSignalEngine(), FinRLSignalEngine()],
        reasoning_engine=builder.reasoning_engine,
    )


async def run_scan(symbol: str, simulate_approval: bool = False) -> dict:
    builder = FrameworkBuilder(get_settings())
    runtime = builder.build()
    pipeline = build_pipeline(builder)
    context, recommendations = await pipeline.analyze(symbol)
    run, recommendations, risks = await runtime.analyze(
        context,
        recommendations,
        broker=BrokerName.PAPER,
        simulate_approval=simulate_approval,
    )
    return {
        "run_id": run.run_id,
        "recommendations": [item.model_dump(mode="json") for item in recommendations],
        "risks": [item.model_dump(mode="json") for item in risks],
    }


async def run_benchmark(symbol: str) -> list[dict]:
    settings = get_settings()
    builder = FrameworkBuilder(settings)
    runtime = builder.build()
    pipeline = build_pipeline(builder)
    context, recommendations = await pipeline.analyze(symbol)
    _, recommendations, _ = await runtime.analyze(
        context,
        recommendations,
        broker=BrokerName.PAPER,
    )
    return [
        benchmark.model_dump(mode="json")
        for benchmark in BenchmarkService().compare(recommendations)
    ]


async def run_investment_plan(
    budget: float,
    symbols: list[str],
    broker: BrokerName = BrokerName.PAPER,
) -> dict:
    settings = get_settings()
    builder = FrameworkBuilder(settings)
    runtime = builder.build()
    pipeline = build_pipeline(builder)
    planner = InvestmentPlanner(runtime, pipeline)
    plan = await planner.plan(
        budget=budget,
        symbols=symbols or ["INFY", "TCS", "RELIANCE", "HDFCBANK", "SBIN"],
        broker=broker,
    )
    return plan.model_dump(mode="json")


def main() -> None:
    parser = argparse.ArgumentParser(prog="ai-trading")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("name", nargs="?", default="my-bot")
    init_parser.add_argument("--template", default="investor-copilot")
    init_parser.add_argument("--broker", default="PAPER", choices=["PAPER", "ZERODHA"])
    init_parser.add_argument("--path", default=".")
    init_parser.add_argument("--no-input", action="store_true")

    subparsers.add_parser("doctor")
    subparsers.add_parser("status")
    subparsers.add_parser("help-bot")

    scan_parser = subparsers.add_parser("scan")
    scan_parser.add_argument("symbol")

    recommend_parser = subparsers.add_parser("recommend")
    recommend_parser.add_argument("symbols", nargs="*")
    recommend_parser.add_argument("--broker", default="PAPER", choices=["PAPER", "ZERODHA"])

    portfolio_parser = subparsers.add_parser("portfolio")
    portfolio_parser.add_argument("--broker", default=None, choices=["PAPER", "ZERODHA"])

    analyze_parser = subparsers.add_parser("analyze")
    analyze_parser.add_argument("symbol")

    backtest_parser = subparsers.add_parser("backtest")
    backtest_parser.add_argument("symbol")

    replay_parser = subparsers.add_parser("replay")
    replay_parser.add_argument("run_id")

    benchmark_parser = subparsers.add_parser("benchmark")
    benchmark_parser.add_argument("symbol", nargs="?", default="INFY")

    invest_parser = subparsers.add_parser("invest")
    invest_parser.add_argument("budget", type=float)
    invest_parser.add_argument("symbols", nargs="*")
    invest_parser.add_argument("--broker", default="PAPER", choices=["PAPER", "ZERODHA"])

    watchlist_parser = subparsers.add_parser("watchlist")
    watchlist_subparsers = watchlist_parser.add_subparsers(dest="watchlist_command", required=True)
    watchlist_add = watchlist_subparsers.add_parser("add")
    watchlist_add.add_argument("symbol")
    watchlist_remove = watchlist_subparsers.add_parser("remove")
    watchlist_remove.add_argument("symbol")
    watchlist_subparsers.add_parser("list")

    subparsers.add_parser("sandbox")

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--host", default=None)
    run_parser.add_argument("--port", type=int, default=None)
    run_parser.add_argument("--reload", action="store_true")
    start_parser = subparsers.add_parser("start")
    start_parser.add_argument("--host", default=None)
    start_parser.add_argument("--port", type=int, default=None)
    start_parser.add_argument("--reload", action="store_true")

    subparsers.add_parser("deploy")
    subparsers.add_parser("connect-telegram")
    subparsers.add_parser("login-zerodha")

    args = parser.parse_args()

    if args.command == "init":
        project_dir = _init_project(
            name=args.name,
            template=args.template,
            broker=BrokerName(args.broker),
            base_path=Path(args.path),
            no_input=args.no_input,
        )
        print(
            f"Initialized bot project at {project_dir}\n"
            f"Next steps:\n"
            f"  cd {project_dir}\n"
            "  ai-trading doctor\n"
            "  ai-trading connect-telegram\n"
            "  ai-trading login-zerodha\n"
            "  ai-trading start"
        )
        return
    if args.command == "doctor":
        print(json.dumps(_doctor(), indent=2))
        return
    if args.command == "status":
        print(json.dumps(_status(), indent=2))
        return
    if args.command == "help-bot":
        print(_bot_help())
        return
    if args.command in {"scan", "analyze", "backtest"}:
        print(
            json.dumps(
                asyncio.run(run_scan(args.symbol, simulate_approval=args.command == "backtest")),
                indent=2,
            )
        )
        return
    if args.command == "recommend":
        print(json.dumps(asyncio.run(_recommend(args.symbols, BrokerName(args.broker))), indent=2))
        return
    if args.command == "portfolio":
        broker = BrokerName(args.broker) if args.broker else None
        print(json.dumps(asyncio.run(_portfolio(broker)), indent=2))
        return
    if args.command == "replay":
        runtime = FrameworkBuilder(get_settings()).build()
        payload = runtime.replay(args.run_id)
        if not payload:
            raise SystemExit(f"Run {args.run_id} not found.")
        print(json.dumps(payload, indent=2))
        return
    if args.command == "benchmark":
        print(json.dumps(asyncio.run(run_benchmark(args.symbol)), indent=2))
        return
    if args.command == "invest":
        print(
            json.dumps(
                asyncio.run(
                    run_investment_plan(
                        budget=args.budget,
                        symbols=args.symbols,
                        broker=BrokerName(args.broker),
                    )
                ),
                indent=2,
            )
        )
        return
    if args.command == "watchlist":
        print(
            json.dumps(
                _watchlist_command(args.watchlist_command, getattr(args, "symbol", None)),
                indent=2,
            )
        )
        return
    if args.command == "sandbox":
        db_path = Path("ai_trading_framework.db").resolve()
        print(
            "Sandbox ready.\n"
            f"Local SQLite store: {db_path}\n"
            "Start the runtime with: ai-trading run --reload"
        )
        return
    if args.command in {"run", "start"}:
        settings = get_settings()
        uvicorn.run(
            "ai_trading_framework.api.app:create_app",
            factory=True,
            host=args.host or settings.api_host,
            port=args.port or settings.api_port,
            reload=args.reload,
        )
        return
    if args.command == "deploy":
        print("Deploy with Railway using railway.json and deploy/docker/Dockerfile.")
        return
    if args.command == "connect-telegram":
        print(json.dumps(asyncio.run(_connect_telegram()), indent=2))
        return
    if args.command == "login-zerodha":
        print(json.dumps(_login_zerodha(), indent=2))


def _project_config_path(project_dir: Path) -> Path:
    return project_dir / "bot.yaml"


def _init_project(
    name: str,
    template: str,
    broker: BrokerName,
    base_path: Path,
    *,
    no_input: bool,
) -> Path:
    project_dir = (base_path / name).resolve()
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "strategies").mkdir(exist_ok=True)
    (project_dir / "prompts").mkdir(exist_ok=True)
    (project_dir / "state").mkdir(exist_ok=True)
    if should_run_interactive_wizard(no_input=no_input):
        config = build_wizard_config(
            name=name,
            template=template,
            broker=broker,
            project_dir=project_dir,
        )
    else:
        try:
            config = load_template_config(template)
            config.name = name
            config.broker = broker
            config.live_trading = broker != BrokerName.PAPER
        except FileNotFoundError:
            config = default_bot_config(
                name=name,
                broker=broker,
                live_trading=broker != BrokerName.PAPER,
                telegram_enabled=True,
            )
    save_bot_config(config, _project_config_path(project_dir))
    (project_dir / ".env.example").write_text(
        "\n".join(
            [
                "BOT_CONFIG_PATH=./bot.yaml",
                "DATABASE_URL=sqlite:///./ai_trading_framework.db",
                "PUBLIC_BASE_URL=http://127.0.0.1:8000",
                "TELEGRAM_BOT_TOKEN=",
                "TELEGRAM_DEFAULT_CHAT_ID=",
                "TELEGRAM_WEBHOOK_SECRET=change-me",
                "ZERODHA_API_KEY=",
                "ZERODHA_API_SECRET=",
                "OPENAI_API_KEY=",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (project_dir / "README.md").write_text(
        "\n".join(
            [
                f"# {name}",
                "",
                f"Template: {template}",
                f"Available templates: {', '.join(available_templates())}",
                "",
                "## Quickstart",
                "",
                "```bash",
                "cp .env.example .env",
                "ai-trading doctor",
                "ai-trading status",
                "ai-trading help-bot",
                "ai-trading connect-telegram",
                "ai-trading login-zerodha",
                "ai-trading start",
                "```",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    for dirname in ("strategies", "prompts", "state"):
        (project_dir / dirname / ".gitkeep").write_text("", encoding="utf-8")
    return project_dir


def _load_local_bot_config() -> tuple[Path, BotConfig]:
    settings = get_settings()
    path = Path(settings.bot_config_path)
    return path, load_bot_config(path)


def _doctor() -> dict[str, object]:
    settings = get_settings()
    config_path, config = _load_local_bot_config()
    zerodha_ready = bool(settings.zerodha_api_key and settings.zerodha_api_secret)
    telegram_ready = bool(settings.telegram_bot_token and settings.telegram_default_chat_id)
    return {
        "config_exists": config_path.exists(),
        "config_path": str(config_path.resolve()),
        "bot_name": config.name,
        "broker": config.broker.value,
        "capabilities": config.capabilities.model_dump(mode="json"),
        "database_url": settings.database_url,
        "runtime_bootable": True,
        "telegram_ready": telegram_ready,
        "telegram_enabled_in_config": config.telegram.enabled,
        "zerodha_ready": zerodha_ready,
        "openai_ready": bool(settings.openai_api_key),
        "watchlist_size": len(config.defaults.watchlist),
    }


def _status() -> dict[str, object]:
    settings = get_settings()
    builder = FrameworkBuilder(settings)
    runtime = builder.build()
    config_path, config = _load_local_bot_config()
    watchlist = WatchlistState(runtime.run_store, config.defaults.watchlist).get_all()
    funds = asyncio.run(runtime.get_funds(config.broker))
    return {
        "config_path": str(config_path.resolve()),
        "bot_name": config.name,
        "broker": config.broker.value,
        "auth_mode": settings.auth_mode,
        "telegram_enabled": bool(settings.telegram_bot_token),
        "zerodha_connected": runtime.get_zerodha_client().is_connected(),
        "capabilities": config.capabilities.model_dump(mode="json"),
        "default_budget": config.defaults.default_budget,
        "funds": funds.model_dump(mode="json") if funds else None,
        "watchlist": watchlist,
        "recommendation_count": len(runtime.list_recommendations()),
    }


async def _connect_telegram() -> dict[str, object]:
    settings = get_settings()
    builder = FrameworkBuilder(settings)
    notifier = builder.notifier
    if not settings.telegram_bot_token:
        return {"ok": False, "detail": "TELEGRAM_BOT_TOKEN is not configured."}
    webhook_url = (
        f"{settings.public_base_url.rstrip('/')}/v1/telegram/webhook/"
        f"{settings.telegram_webhook_secret}"
    )
    payload = await notifier.set_webhook(
        webhook_url,
        secret_token=settings.telegram_webhook_secret,
    )
    return {
        "webhook_url": webhook_url,
        "secret_token": settings.telegram_webhook_secret,
        "result": payload,
    }


def _login_zerodha() -> dict[str, object]:
    settings = get_settings()
    runtime = FrameworkBuilder(settings).build()
    url = runtime.get_zerodha_client().login_url()
    if not url:
        return {"ok": False, "detail": "ZERODHA_API_KEY is not configured."}
    if os.environ.get("CI") != "true":
        try:
            webbrowser.open(url)
        except Exception:
            pass
    callback_url = f"{settings.public_base_url.rstrip('/')}/v1/brokers/zerodha/callback"
    return {"ok": True, "login_url": url, "callback_url": callback_url}


def _watchlist_command(command: str, symbol: str | None) -> dict[str, object]:
    settings = get_settings()
    runtime = FrameworkBuilder(settings).build()
    _, config = _load_local_bot_config()
    state = WatchlistState(runtime.run_store, config.defaults.watchlist)
    if command == "list":
        return {"items": state.get_all()}
    if command == "add" and symbol:
        return {"items": state.add(symbol)}
    if command == "remove" and symbol:
        return {"items": state.remove(symbol)}
    raise SystemExit("Unsupported watchlist command.")


async def _recommend(symbols: list[str], broker: BrokerName) -> dict[str, object]:
    settings = get_settings()
    builder = FrameworkBuilder(settings)
    runtime = builder.build()
    pipeline = build_pipeline(builder)
    _, config = _load_local_bot_config()
    router = ProductRouter(config=config, runtime=runtime, pipeline=pipeline)
    return await router.recommend_now(
        broker=broker,
        symbols=[symbol.upper() for symbol in symbols] if symbols else None,
        notify=False,
    )


async def _portfolio(broker: BrokerName | None) -> dict[str, object]:
    settings = get_settings()
    builder = FrameworkBuilder(settings)
    runtime = builder.build()
    pipeline = build_pipeline(builder)
    _, config = _load_local_bot_config()
    router = ProductRouter(config=config, runtime=runtime, pipeline=pipeline)
    return await router.summarize_portfolio(broker)


def _bot_help() -> str:
    _, config = _load_local_bot_config()
    from ai_trading_framework.product.capabilities.help import HelpCapability

    return HelpCapability(config.capabilities).render()
