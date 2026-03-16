from __future__ import annotations

from ai_trading_framework.brokers.base import BaseBrokerClient
from ai_trading_framework.models import (
    BrokerCapabilities,
    ExecutionResult,
    OrderPreview,
    OrderRequest,
)


class GrowwBrokerClient(BaseBrokerClient):
    capabilities = BrokerCapabilities(supports_intraday=True, supports_websocket=True)

    async def preview_order(self, order_request: OrderRequest) -> OrderPreview:
        return OrderPreview(
            recommendation_id=order_request.recommendation_id,
            broker=order_request.broker,
            action=order_request.action,
            symbol=order_request.symbol,
            quantity=order_request.quantity,
            order_type=order_request.order_type,
            estimated_notional=0.0,
            warnings=["Groww remains experimental in v1."],
        )

    async def submit_order(self, order_request: OrderRequest) -> ExecutionResult:
        return ExecutionResult(
            recommendation_id=order_request.recommendation_id,
            broker=order_request.broker,
            status="REJECTED",
            message="Groww support is experimental in v1.",
        )

    async def get_positions(self) -> list:
        return []

    async def get_holdings(self) -> list:
        return []
