from __future__ import annotations

from ai_trading_framework.core.plugin_system.interfaces import LLMProvider, ReasoningEngine
from ai_trading_framework.models import Action, EvaluatedSignal, MarketContext, Recommendation
from ai_trading_framework.reasoning.llm import HeuristicLLMProvider


class DebateReasoningEngine(ReasoningEngine):
    def __init__(self, llm_provider: LLMProvider | None = None) -> None:
        self.llm_provider = llm_provider or HeuristicLLMProvider()

    async def analyze(
        self, evaluated_signal: EvaluatedSignal, market_context: MarketContext
    ) -> Recommendation:
        thesis = await self.llm_provider.complete(
            "\n".join(
                [
                    f"Symbol: {evaluated_signal.symbol}",
                    f"Action: {evaluated_signal.action.value}",
                    f"Confidence: {evaluated_signal.confidence}",
                    f"Factors: {', '.join(evaluated_signal.factors)}",
                ]
            )
        )
        entry = market_context.price.price
        target = (
            round(entry * 1.05, 2)
            if evaluated_signal.action == Action.BUY
            else round(entry * 0.95, 2)
        )
        stop = (
            round(entry * 0.97, 2)
            if evaluated_signal.action == Action.BUY
            else round(entry * 1.03, 2)
        )
        return Recommendation(
            symbol=evaluated_signal.symbol,
            action=evaluated_signal.action,
            confidence=evaluated_signal.confidence,
            thesis=thesis,
            strategy_name=evaluated_signal.metadata.get("strategy_name", "unknown"),
            supporting_evidence=evaluated_signal.factors,
            key_risks=["Macro weakness", "Signal decay if price rejects entry"],
            entry_price=entry,
            stop_loss=stop,
            target=target,
            signal=evaluated_signal,
        )
