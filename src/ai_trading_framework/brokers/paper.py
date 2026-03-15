from __future__ import annotations

from ai_trading_framework.brokers.base import BaseBrokerClient
from ai_trading_framework.data.providers.base import MarketDataProvider
from ai_trading_framework.models import ExecutionResult, OrderPreview, OrderRequest, Position


class PaperBrokerClient(BaseBrokerClient):
    def __init__(self, market_data_provider: MarketDataProvider) -> None:
        self.market_data_provider = market_data_provider
        self.positions: list[Position] = []

    async def preview_order(self, order_request: OrderRequest) -> OrderPreview:
        snapshot = await self.market_data_provider.get_price(order_request.symbol)
        estimated = order_request.quantity * (order_request.limit_price or snapshot.price)
        return OrderPreview(
            recommendation_id=order_request.recommendation_id,
            broker=order_request.broker,
            action=order_request.action,
            symbol=order_request.symbol,
            quantity=order_request.quantity,
            order_type=order_request.order_type,
            estimated_notional=estimated,
        )

    async def submit_order(self, order_request: OrderRequest) -> ExecutionResult:
        snapshot = await self.market_data_provider.get_price(order_request.symbol)
        fill_price = order_request.limit_price or order_request.stop_price or snapshot.price
        self.positions.append(
            Position(
                symbol=order_request.symbol,
                quantity=order_request.quantity,
                average_price=fill_price,
                market_price=fill_price,
            )
        )
        return ExecutionResult(
            recommendation_id=order_request.recommendation_id,
            broker=order_request.broker,
            status="FILLED",
            message="Paper order filled.",
            fill_price=fill_price,
            filled_quantity=order_request.quantity,
            broker_order_id=f"paper-{order_request.recommendation_id}",
        )

    async def get_positions(self) -> list[Position]:
        return list(self.positions)
