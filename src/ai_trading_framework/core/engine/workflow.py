from __future__ import annotations

from ai_trading_framework.core.approvals.service import ApprovalService
from ai_trading_framework.core.events.bus import EventBus
from ai_trading_framework.core.explainability.service import ExplainabilityEngine
from ai_trading_framework.execution.service import ExecutionService
from ai_trading_framework.models import (
    BrokerName,
    Event,
    EventType,
    MarketContext,
    OrderRequest,
    OrderType,
    Recommendation,
    RiskEvaluation,
    RunRecord,
)
from ai_trading_framework.risk.policies.base import RiskPolicyChain


class WorkflowEngine:
    def __init__(
        self,
        event_bus: EventBus,
        explainability: ExplainabilityEngine,
        approval_service: ApprovalService,
        risk_chain: RiskPolicyChain,
        execution_service: ExecutionService,
    ) -> None:
        self.event_bus = event_bus
        self.explainability = explainability
        self.approval_service = approval_service
        self.risk_chain = risk_chain
        self.execution_service = execution_service

    async def process(
        self,
        context: MarketContext,
        recommendations: list[Recommendation],
        broker: BrokerName,
        simulate_approval: bool = False,
    ) -> tuple[RunRecord, list[Recommendation], list[RiskEvaluation]]:
        run = RunRecord(symbol=context.symbol)
        await self.append_event(
            run,
            EventType.MARKET_CONTEXT_BUILT,
            {"symbol": context.symbol, "price": context.price.model_dump(mode="json")},
        )
        risk_evaluations: list[RiskEvaluation] = []
        for recommendation in recommendations:
            recommendation.run_id = run.run_id
            await self.append_event(
                run, EventType.RECOMMENDATION_CREATED, recommendation.model_dump(mode="json")
            )
            risk = await self.risk_chain.evaluate(recommendation, context.portfolio_state, context)
            risk_evaluations.append(risk)
            await self.append_event(run, EventType.RISK_EVALUATED, risk.model_dump(mode="json"))
            explanation = self.explainability.generate(recommendation, context, risk)
            recommendation.explanation = explanation
            await self.append_event(
                run, EventType.EXPLANATION_GENERATED, explanation.model_dump(mode="json")
            )
            approval = self.approval_service.request(
                recommendation.recommendation_id, run.run_id, broker
            )
            await self.append_event(
                run, EventType.APPROVAL_REQUESTED, approval.model_dump(mode="json")
            )
            if simulate_approval and broker != BrokerName.PAPER:
                approval = self.approval_service.approve(
                    recommendation.recommendation_id, approval.token
                )
                await self.append_event(
                    run, EventType.APPROVAL_GRANTED, approval.model_dump(mode="json")
                )
        return run, recommendations, risk_evaluations

    async def preview_and_execute(
        self,
        run: RunRecord,
        recommendation: Recommendation,
        quantity: int,
        broker: BrokerName,
        risk_evaluation: RiskEvaluation,
        order_type: OrderType = OrderType.LIMIT,
        approval_token: str | None = None,
        limit_price: float | None = None,
        stop_price: float | None = None,
    ):
        order_request = OrderRequest(
            recommendation_id=recommendation.recommendation_id,
            approval_token=approval_token,
            symbol=recommendation.symbol,
            broker=broker,
            action=recommendation.action,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price or recommendation.entry_price,
            stop_price=stop_price or recommendation.stop_loss,
        )
        await self.append_event(
            run, EventType.EXECUTION_REQUESTED, order_request.model_dump(mode="json")
        )
        preview = await self.execution_service.preview_order(order_request)
        result = await self.execution_service.execute(
            recommendation, order_request, risk_evaluation.decision
        )
        event_type = (
            EventType.EXECUTION_COMPLETED
            if result.status not in {"REJECTED", "FAILED"}
            else EventType.EXECUTION_FAILED
        )
        await self.append_event(run, event_type, result.model_dump(mode="json"))
        return preview, result

    async def append_event(self, run: RunRecord, event_type: EventType, payload: dict) -> None:
        event = Event(event_type=event_type, run_id=run.run_id, payload=payload)
        run.events.append(event)
        await self.event_bus.publish(event)
