from __future__ import annotations

from ai_trading_framework.models import (
    MarketContext,
    Recommendation,
    RecommendationExplanation,
    RiskEvaluation,
)


class ExplainabilityEngine:
    def generate(
        self,
        recommendation: Recommendation,
        market_context: MarketContext,
        risk_evaluation: RiskEvaluation,
    ) -> RecommendationExplanation:
        return RecommendationExplanation(
            why_this_trade=recommendation.thesis,
            signals_used=recommendation.supporting_evidence,
            risk_checks=[reason for check in risk_evaluation.checks for reason in check.reasons],
            ai_reasoning=(
                f"{recommendation.action.value} {recommendation.symbol} because the "
                "strategy score, news tone, "
                f"and reasoning engine aligned at confidence {recommendation.confidence:.2f}."
            ),
            execution_constraints=[
                "Broker approval required before execution on "
                f"{market_context.metadata.get('broker', 'PAPER')}.",
                "Execution blocks if approval token is missing, expired, or already consumed.",
            ],
        )
