from __future__ import annotations

from collections.abc import Mapping

from ai_trading_framework.core.approvals.service import ApprovalService
from ai_trading_framework.core.plugin_system.interfaces import BrokerClient
from ai_trading_framework.models import (
    BrokerName,
    ExecutionResult,
    OrderPreview,
    OrderRequest,
    Recommendation,
    RiskDecision,
)


class ExecutionService:
    def __init__(
        self,
        approval_service: ApprovalService,
        brokers: Mapping[BrokerName, BrokerClient],
    ) -> None:
        self.approval_service = approval_service
        self.brokers = brokers

    async def preview_order(self, order_request: OrderRequest) -> OrderPreview:
        broker = self.brokers[order_request.broker]
        return await broker.preview_order(order_request)

    async def execute(
        self,
        recommendation: Recommendation,
        order_request: OrderRequest,
        risk_decision: RiskDecision,
    ) -> ExecutionResult:
        if order_request.broker != BrokerName.PAPER:
            if risk_decision != RiskDecision.APPROVED:
                return ExecutionResult(
                    recommendation_id=order_request.recommendation_id,
                    broker=order_request.broker,
                    status="REJECTED",
                    message="Execution blocked because risk policy did not approve the trade.",
                )
            if not order_request.approval_token:
                return ExecutionResult(
                    recommendation_id=order_request.recommendation_id,
                    broker=order_request.broker,
                    status="REJECTED",
                    message="Execution blocked because approval token is missing.",
                )
            self.approval_service.consume(
                recommendation.recommendation_id, order_request.approval_token
            )
        broker = self.brokers[order_request.broker]
        return await broker.submit_order(order_request)
