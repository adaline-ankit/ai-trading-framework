from __future__ import annotations

from collections.abc import Sequence

from ai_trading_framework.core.plugin_system.interfaces import SignalBatchItem, SignalEngine
from ai_trading_framework.models import Action, EvaluatedSignal, MarketContext


class FinRLSignalEngine(SignalEngine):
    async def evaluate(
        self,
        signals: Sequence[SignalBatchItem],
        market_context: MarketContext,
    ) -> list[EvaluatedSignal]:
        evaluated: list[EvaluatedSignal] = []
        for signal in signals:
            bias = (
                0.05 if market_context.sentiment and market_context.sentiment.score > 0 else -0.05
            )
            score = round(signal.confidence + bias, 4)
            action = signal.action
            if score < 0.5 and action != Action.HOLD:
                action = Action.HOLD
            strategy_name = getattr(signal, "strategy_name", None) or signal.metadata.get(
                "strategy_name", "unknown"
            )
            evaluated.append(
                EvaluatedSignal(
                    signal_id=signal.signal_id,
                    symbol=signal.symbol,
                    action=action,
                    confidence=min(max(score, 0.45), 0.95),
                    score=score,
                    factors=[
                        "FinRL-style heuristic score",
                        f"Sentiment modifier {bias:+.2f}",
                    ],
                    metadata={"strategy_name": strategy_name, **signal.metadata},
                )
            )
        return evaluated
