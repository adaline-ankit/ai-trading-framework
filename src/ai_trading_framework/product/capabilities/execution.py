from __future__ import annotations

from typing import Any

from ai_trading_framework.core.runtime.operator import OperatorRuntime
from ai_trading_framework.models import BrokerName, OrderType


class ExecutionCapability:
    def __init__(self, runtime: OperatorRuntime) -> None:
        self.runtime = runtime

    async def approve(self, recommendation_id: str) -> dict[str, Any]:
        approval = await self.runtime.approve_with_stored_token(recommendation_id)
        return approval.model_dump(mode="json")

    async def reject(self, recommendation_id: str) -> dict[str, Any]:
        approval = await self.runtime.reject_with_stored_token(recommendation_id)
        return approval.model_dump(mode="json")

    async def preview(
        self,
        recommendation_id: str,
        *,
        broker: BrokerName,
        quantity: float = 1.0,
        order_type: OrderType = OrderType.LIMIT,
    ) -> dict[str, Any]:
        preview = await self.runtime.preview_order(
            recommendation_id=recommendation_id,
            broker=broker,
            quantity=quantity,
            order_type=order_type,
        )
        return preview.model_dump(mode="json")

    async def submit(
        self,
        recommendation_id: str,
        *,
        broker: BrokerName,
        quantity: float = 1.0,
        order_type: OrderType = OrderType.LIMIT,
    ) -> dict[str, Any]:
        approval = self.runtime.get_approval(recommendation_id)
        preview, result = await self.runtime.submit_order(
            recommendation_id=recommendation_id,
            broker=broker,
            quantity=quantity,
            order_type=order_type,
            approval_token=approval.token if approval else None,
        )
        return {
            "preview": preview.model_dump(mode="json"),
            "result": result.model_dump(mode="json"),
        }
