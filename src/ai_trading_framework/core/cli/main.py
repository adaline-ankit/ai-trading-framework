from __future__ import annotations

import argparse
import asyncio
import json
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

    subparsers.add_parser("init")

    scan_parser = subparsers.add_parser("scan")
    scan_parser.add_argument("symbol")

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

    subparsers.add_parser("sandbox")

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--host", default=None)
    run_parser.add_argument("--port", type=int, default=None)
    run_parser.add_argument("--reload", action="store_true")

    subparsers.add_parser("deploy")

    args = parser.parse_args()

    if args.command == "init":
        print("Initialized ai-trading-framework project structure.")
        return
    if args.command in {"scan", "analyze", "backtest"}:
        print(
            json.dumps(
                asyncio.run(run_scan(args.symbol, simulate_approval=args.command == "backtest")),
                indent=2,
            )
        )
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
    if args.command == "sandbox":
        db_path = Path("ai_trading_framework.db").resolve()
        print(
            "Sandbox ready.\n"
            f"Local SQLite store: {db_path}\n"
            "Start the runtime with: ai-trading run --reload"
        )
        return
    if args.command == "run":
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
