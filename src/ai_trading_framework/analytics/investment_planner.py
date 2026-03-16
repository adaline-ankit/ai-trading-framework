from __future__ import annotations

from collections.abc import Sequence
from math import floor

from ai_trading_framework.core.orchestration.pipeline import AnalysisPipeline
from ai_trading_framework.core.runtime.operator import OperatorRuntime
from ai_trading_framework.models import (
    Action,
    AssetClass,
    BrokerName,
    InvestmentCandidate,
    InvestmentPlan,
    Recommendation,
    RiskDecision,
)


class InvestmentPlanner:
    def __init__(self, runtime: OperatorRuntime, pipeline: AnalysisPipeline) -> None:
        self.runtime = runtime
        self.pipeline = pipeline

    async def plan(
        self,
        *,
        budget: float,
        symbols: Sequence[str],
        broker: BrokerName,
    ) -> InvestmentPlan:
        normalized_symbols = [symbol.upper() for symbol in symbols if symbol.strip()]
        candidates: list[InvestmentCandidate] = []
        selected_recommendation: Recommendation | None = None

        for symbol in normalized_symbols:
            context, recommendations = await self.pipeline.analyze(symbol, broker=broker)
            _, analyzed_recommendations, risks = await self.runtime.analyze(
                context,
                recommendations,
                broker=broker,
                notify=False,
            )
            for recommendation, risk in zip(analyzed_recommendations, risks, strict=False):
                candidate = self._candidate_from_recommendation(
                    recommendation=recommendation,
                    risk_decision=risk.decision,
                    budget=budget,
                )
                if candidate:
                    candidates.append(candidate)
                    if recommendation.recommendation_id == candidate.recommendation_id:
                        if not selected_recommendation:
                            selected_recommendation = recommendation

        candidates.sort(key=lambda item: item.score, reverse=True)
        selected = candidates[0] if candidates else None
        if selected:
            selected_recommendation = self.runtime.get_recommendation(selected.recommendation_id)
        approval = (
            self.runtime.get_approval(selected.recommendation_id)
            if selected and selected_recommendation
            else None
        )
        if selected and selected_recommendation and approval and self.runtime.notifier:
            await self.runtime.notifier.send_recommendation(selected_recommendation, approval.token)

        summary = (
            f"Best candidate is {selected.symbol} with {selected.confidence:.0%} confidence "
            f"at estimated entry {selected.estimated_entry_price:.2f}."
            if selected
            else "No approved BUY idea fits the current budget and risk filters."
        )
        next_step = (
            "Approve the recommendation and submit the suggested quantity through the existing "
            "order preview and submit flow."
            if selected
            else "Broaden the symbol list, increase budget, or review risk settings."
        )
        return InvestmentPlan(
            broker=broker,
            budget=budget,
            symbols_considered=normalized_symbols,
            selected=selected,
            alternatives=candidates[1:5] if len(candidates) > 1 else [],
            recommendation=selected_recommendation,
            approval=approval,
            summary=summary,
            next_step=next_step,
        )

    def _candidate_from_recommendation(
        self,
        *,
        recommendation: Recommendation,
        risk_decision: RiskDecision,
        budget: float,
    ) -> InvestmentCandidate | None:
        if recommendation.action != Action.BUY:
            return None
        if risk_decision != RiskDecision.APPROVED:
            return None
        entry_price = float(recommendation.entry_price or 0.0)
        if entry_price <= 0:
            return None
        asset_class = (
            recommendation.instrument.asset_class
            if recommendation.instrument
            else AssetClass.UNKNOWN
        )
        quantity = self._suggest_quantity(
            budget=budget,
            entry_price=entry_price,
            asset_class=asset_class,
        )
        if quantity <= 0:
            return None
        upside = max((float(recommendation.target or entry_price) - entry_price) / entry_price, 0.0)
        score = round((recommendation.confidence * 0.8) + (upside * 0.2), 4)
        return InvestmentCandidate(
            symbol=recommendation.symbol,
            recommendation_id=recommendation.recommendation_id,
            action=recommendation.action,
            confidence=recommendation.confidence,
            score=score,
            estimated_entry_price=entry_price,
            estimated_notional=round(quantity * entry_price, 2),
            suggested_quantity=quantity,
            risk_decision=risk_decision,
            thesis=recommendation.thesis,
            asset_class=asset_class,
        )

    @staticmethod
    def _suggest_quantity(*, budget: float, entry_price: float, asset_class: AssetClass) -> float:
        if budget <= 0 or entry_price <= 0:
            return 0.0
        if asset_class == AssetClass.MUTUAL_FUND:
            return round(budget / entry_price, 3)
        quantity = floor(budget / entry_price)
        return float(max(quantity, 0))
