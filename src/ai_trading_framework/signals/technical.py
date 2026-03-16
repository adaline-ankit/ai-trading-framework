from __future__ import annotations

from collections.abc import Sequence

from ai_trading_framework.core.plugin_system.interfaces import SignalBatchItem, SignalEngine
from ai_trading_framework.models import (
    Action,
    EvaluatedSignal,
    MarketContext,
    Recommendation,
    Signal,
)
from ai_trading_framework.sdk.strategies.base import TradingStrategy


class MomentumStrategy(TradingStrategy):
    name = "momentum_strategy"
    tags = ["technical", "momentum"]

    async def scan(self, market_context: MarketContext) -> list[Signal]:
        closes = [candle.close for candle in market_context.candles[-10:]]
        if len(closes) < 2:
            return []
        change = (closes[-1] - closes[0]) / max(closes[0], 1.0)
        action = Action.BUY if change > 0.01 else Action.SELL if change < -0.01 else Action.HOLD
        confidence = min(max(abs(change) * 8, 0.52), 0.9)
        return [
            Signal(
                symbol=market_context.symbol,
                instrument=market_context.instrument,
                strategy_name=self.name,
                action=action,
                confidence=round(confidence, 4),
                rationale=f"10-period momentum change is {change:.2%}.",
                metadata={"momentum_change": round(change, 4)},
            )
        ]

    async def analyze(self, signal: Signal, context: MarketContext) -> Recommendation | None:
        return None


class MomentumSignalEngine(SignalEngine):
    async def evaluate(
        self, signals: Sequence[SignalBatchItem], market_context: MarketContext
    ) -> list[EvaluatedSignal]:
        evaluated: list[EvaluatedSignal] = []
        for signal in signals:
            strategy_name = getattr(signal, "strategy_name", None) or signal.metadata.get(
                "strategy_name", "unknown"
            )
            rationale = getattr(signal, "rationale", None) or "Signal evaluation input."
            evaluated.append(
                EvaluatedSignal(
                    signal_id=signal.signal_id,
                    symbol=signal.symbol,
                    instrument=getattr(signal, "instrument", None),
                    action=signal.action,
                    confidence=signal.confidence,
                    score=round(
                        signal.confidence
                        * (
                            1
                            if signal.action == Action.BUY
                            else -1
                            if signal.action == Action.SELL
                            else 0
                        ),
                        4,
                    ),
                    factors=[
                        rationale,
                        f"Price change {market_context.price.change_percent}%",
                    ],
                    metadata={"strategy_name": strategy_name, **signal.metadata},
                )
            )
        return evaluated
