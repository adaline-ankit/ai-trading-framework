from __future__ import annotations

from ai_trading_framework.core.plugin_system.interfaces import RiskPolicy
from ai_trading_framework.models import (
    MarketContext,
    PortfolioState,
    Recommendation,
    RiskCheckResult,
    RiskDecision,
    RiskEvaluation,
)


class RiskPolicyChain:
    def __init__(self, policies: list[RiskPolicy]) -> None:
        self.policies = policies

    async def evaluate(
        self,
        recommendation: Recommendation,
        portfolio_state: PortfolioState,
        market_context: MarketContext,
    ) -> RiskEvaluation:
        checks: list[RiskCheckResult] = []
        decision = RiskDecision.APPROVED
        max_position_size: int | None = None
        for policy in self.policies:
            result = await policy.validate(recommendation, portfolio_state, market_context)
            checks.extend(result.checks)
            if result.max_position_size is not None:
                max_position_size = result.max_position_size
            if result.decision == RiskDecision.REJECTED:
                decision = RiskDecision.REJECTED
                break
            if result.decision == RiskDecision.REVIEW and decision != RiskDecision.REJECTED:
                decision = RiskDecision.REVIEW
        summary = (
            "Risk policy chain approved the recommendation."
            if decision == RiskDecision.APPROVED
            else "Risk policy chain requires review."
            if decision == RiskDecision.REVIEW
            else "Risk policy chain rejected the recommendation."
        )
        return RiskEvaluation(
            decision=decision,
            summary=summary,
            checks=checks,
            max_position_size=max_position_size,
        )
