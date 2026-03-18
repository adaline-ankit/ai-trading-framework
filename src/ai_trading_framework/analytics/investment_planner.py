from __future__ import annotations

from collections.abc import Sequence
from math import floor

from ai_trading_framework.core.orchestration.pipeline import AnalysisPipeline
from ai_trading_framework.core.runtime.operator import OperatorRuntime
from ai_trading_framework.models import (
    Action,
    AllocationPlanItem,
    AssetClass,
    BrokerName,
    InvestmentCandidate,
    InvestmentPlan,
    Position,
    RebalanceAction,
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
        positions = await self.runtime.get_holdings(broker)
        holdings_index = self._position_index(positions)
        portfolio_value = self._portfolio_value(positions)

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
                    holdings_index=holdings_index,
                    portfolio_value=portfolio_value,
                )
                if candidate:
                    candidates.append(candidate)
                    if recommendation.recommendation_id == candidate.recommendation_id:
                        if not selected_recommendation:
                            selected_recommendation = recommendation

        candidates.sort(key=lambda item: item.score, reverse=True)
        selected = candidates[0] if candidates else None
        allocations = self._build_allocations(candidates, budget)
        rebalance_actions = self._build_rebalance_actions(
            positions=positions,
            allocations=allocations,
            candidates=candidates,
        )
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
            (
                f"Top idea is {selected.symbol} with {selected.confidence:.0%} confidence. "
                f"Allocated across {len(allocations)} idea(s) with "
                f"{len(rebalance_actions)} rebalance suggestion(s)."
            )
            if selected
            else "No approved BUY idea fits the current budget, holdings, and risk filters."
        )
        next_step = (
            "Review the allocation plan, inspect rebalance actions, then approve and submit "
            "the selected recommendation through the existing order preview flow."
            if selected
            else "Broaden the symbol list, increase budget, or review risk settings."
        )
        return InvestmentPlan(
            broker=broker,
            budget=budget,
            symbols_considered=normalized_symbols,
            selected=selected,
            alternatives=candidates[1:5] if len(candidates) > 1 else [],
            allocations=allocations,
            rebalance_actions=rebalance_actions,
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
        holdings_index: dict[str, Position],
        portfolio_value: float,
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
        current_position = holdings_index.get(recommendation.symbol.upper())
        current_notional = (
            current_position.quantity * current_position.market_price if current_position else 0.0
        )
        current_weight = current_notional / portfolio_value if portfolio_value > 0 else 0.0
        exposure_penalty = min(current_weight, 0.5)
        score = round(
            (recommendation.confidence * 0.75) + (upside * 0.2) - (exposure_penalty * 0.25),
            4,
        )
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
    def _position_index(positions: Sequence[Position]) -> dict[str, Position]:
        return {position.symbol.upper(): position for position in positions}

    @staticmethod
    def _portfolio_value(positions: Sequence[Position]) -> float:
        return sum(position.quantity * position.market_price for position in positions)

    def _build_allocations(
        self,
        candidates: Sequence[InvestmentCandidate],
        budget: float,
    ) -> list[AllocationPlanItem]:
        shortlisted = list(candidates[:3])
        if not shortlisted or budget <= 0:
            return []
        total_score = sum(candidate.score for candidate in shortlisted) or 1.0
        allocations: list[AllocationPlanItem] = []
        remaining_budget = budget
        for index, candidate in enumerate(shortlisted):
            if index == len(shortlisted) - 1:
                allocated_budget = remaining_budget
            else:
                allocated_budget = round(budget * (candidate.score / total_score), 2)
                remaining_budget = max(round(remaining_budget - allocated_budget, 2), 0.0)
            quantity = self._suggest_quantity(
                budget=allocated_budget,
                entry_price=candidate.estimated_entry_price,
                asset_class=candidate.asset_class,
            )
            if quantity <= 0:
                continue
            estimated_notional = round(quantity * candidate.estimated_entry_price, 2)
            allocations.append(
                AllocationPlanItem(
                    symbol=candidate.symbol,
                    recommendation_id=candidate.recommendation_id,
                    allocated_budget=round(allocated_budget, 2),
                    target_weight=round(allocated_budget / budget, 4),
                    suggested_quantity=quantity,
                    estimated_entry_price=candidate.estimated_entry_price,
                    estimated_notional=estimated_notional,
                    reason=f"Allocated by score {candidate.score:.2f} and conviction.",
                )
            )
        return allocations

    def _build_rebalance_actions(
        self,
        *,
        positions: Sequence[Position],
        allocations: Sequence[AllocationPlanItem],
        candidates: Sequence[InvestmentCandidate],
    ) -> list[RebalanceAction]:
        if not positions:
            return []
        target_weights = {item.symbol.upper(): item.target_weight for item in allocations}
        portfolio_value = self._portfolio_value(positions)
        if portfolio_value <= 0:
            return []
        candidate_symbols = {candidate.symbol.upper() for candidate in candidates[:3]}
        max_concentration = 0.45
        actions: list[RebalanceAction] = []
        for position in positions:
            symbol = position.symbol.upper()
            current_value = position.quantity * position.market_price
            current_weight = current_value / portfolio_value
            target_weight = target_weights.get(symbol, 0.0)
            quantity_delta = 0.0
            action = "HOLD"
            reason = "Current allocation is acceptable."
            if current_weight > max_concentration:
                action = "TRIM"
                target_weight = min(max(target_weight, 0.2), max_concentration)
                target_value = portfolio_value * target_weight
                quantity_delta = round((current_value - target_value) / position.market_price, 2)
                reason = (
                    "Holding exceeds the concentration guardrail for a balanced portfolio plan."
                )
            elif symbol not in candidate_symbols and current_weight > 0.35:
                action = "TRIM"
                target_weight = 0.2
                target_value = portfolio_value * target_weight
                quantity_delta = round((current_value - target_value) / position.market_price, 2)
                reason = (
                    "Holding is above concentration threshold and not in the top allocation set."
                )
            elif target_weight and current_weight < target_weight * 0.7:
                action = "ADD"
                target_value = portfolio_value * target_weight
                quantity_delta = round((target_value - current_value) / position.market_price, 2)
                reason = (
                    "Holding is below the target allocation implied by current recommendations."
                )
            elif target_weight and current_weight > target_weight * 1.3:
                action = "TRIM"
                target_value = portfolio_value * target_weight
                quantity_delta = round((current_value - target_value) / position.market_price, 2)
                reason = (
                    "Holding is above the target allocation implied by current recommendations."
                )
            if action != "HOLD":
                actions.append(
                    RebalanceAction(
                        symbol=position.symbol,
                        action=action,
                        current_weight=round(current_weight, 4),
                        target_weight=round(target_weight, 4),
                        quantity_delta=max(quantity_delta, 0.0),
                        reason=reason,
                    )
                )
        return actions

    @staticmethod
    def _suggest_quantity(*, budget: float, entry_price: float, asset_class: AssetClass) -> float:
        if budget <= 0 or entry_price <= 0:
            return 0.0
        if asset_class == AssetClass.MUTUAL_FUND:
            return round(budget / entry_price, 3)
        quantity = floor(budget / entry_price)
        return float(max(quantity, 0))
