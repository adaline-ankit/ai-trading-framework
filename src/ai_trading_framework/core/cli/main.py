from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

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


def main() -> None:
    parser = argparse.ArgumentParser(prog="ai-trading")
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

    subparsers.add_parser("benchmark")
    subparsers.add_parser("sandbox")
    subparsers.add_parser("run")
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
        print(json.dumps(asyncio.run(run_scan("INFY")), indent=2))
        return
    if args.command == "sandbox":
        db_path = Path("ai_trading_framework.db").resolve()
        print(f"Sandbox ready. Local SQLite store: {db_path}")
        return
    if args.command == "run":
        print(
            "Run the API with: uvicorn ai_trading_framework.api.app:create_app --factory --reload"
        )
        return
    if args.command == "deploy":
        print("Deploy with Railway using railway.json and deploy/docker/Dockerfile.")
