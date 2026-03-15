from __future__ import annotations

import hashlib
from urllib.parse import quote_plus

import httpx

from ai_trading_framework.brokers.base import BaseBrokerClient
from ai_trading_framework.models import (
    BrokerCapabilities,
    ExecutionResult,
    OrderPreview,
    OrderRequest,
    Position,
)


class ZerodhaBrokerClient(BaseBrokerClient):
    capabilities = BrokerCapabilities(supports_intraday=True, supports_websocket=True)

    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        access_token: str | None = None,
    ) -> None:
        self.api_key = api_key or ""
        self.api_secret = api_secret or ""
        self.access_token = access_token or ""

    def login_url(self) -> str | None:
        if not self.api_key:
            return None
        return f"https://kite.zerodha.com/connect/login?v=3&api_key={quote_plus(self.api_key)}"

    def checksum(self, request_token: str) -> str:
        return hashlib.sha256(
            f"{self.api_key}{request_token}{self.api_secret}".encode()
        ).hexdigest()

    async def preview_order(self, order_request: OrderRequest) -> OrderPreview:
        price = order_request.limit_price or order_request.stop_price or 0.0
        return OrderPreview(
            recommendation_id=order_request.recommendation_id,
            broker=order_request.broker,
            action=order_request.action,
            symbol=order_request.symbol,
            quantity=order_request.quantity,
            order_type=order_request.order_type,
            estimated_notional=order_request.quantity * price,
            warnings=[
                "Live broker execution requires explicit approval and configured credentials."
            ],
        )

    async def submit_order(self, order_request: OrderRequest) -> ExecutionResult:
        if not (self.api_key and self.access_token):
            return ExecutionResult(
                recommendation_id=order_request.recommendation_id,
                broker=order_request.broker,
                status="REJECTED",
                message="Zerodha credentials are not configured.",
            )
        # The v1 framework keeps live submission minimal and explicit.
        return ExecutionResult(
            recommendation_id=order_request.recommendation_id,
            broker=order_request.broker,
            status="PENDING",
            message=(
                "Zerodha live execution adapter is approval-first. "
                "Submit integration remains explicit for deployers."
            ),
        )

    async def get_positions(self) -> list[Position]:
        if not (self.api_key and self.access_token):
            return []
        headers = {
            "X-Kite-Version": "3",
            "Authorization": f"token {self.api_key}:{self.access_token}",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                "https://api.kite.trade/portfolio/positions", headers=headers
            )
        if response.status_code >= 400:
            return []
        payload = response.json().get("data", {})
        return [
            Position(
                symbol=item.get("tradingsymbol") or "UNKNOWN",
                quantity=int(item.get("quantity") or 0),
                average_price=float(item.get("average_price") or 0.0),
                market_price=float(item.get("last_price") or 0.0),
                unrealized_pnl=float(item.get("pnl") or 0.0),
            )
            for item in payload.get("net", [])
        ]
