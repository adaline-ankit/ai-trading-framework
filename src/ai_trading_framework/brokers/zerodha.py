from __future__ import annotations

import hashlib
from urllib.parse import quote_plus

import httpx

from ai_trading_framework.brokers.base import BaseBrokerClient
from ai_trading_framework.models import (
    Action,
    BrokerAuthSession,
    BrokerCapabilities,
    BrokerName,
    ExecutionResult,
    OrderPreview,
    OrderRequest,
    OrderType,
    Position,
    utcnow,
)
from ai_trading_framework.storage.sqlalchemy.repository import SQLAlchemyRunStore


class ZerodhaBrokerClient(BaseBrokerClient):
    capabilities = BrokerCapabilities(supports_intraday=True, supports_websocket=True)

    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        access_token: str | None = None,
        *,
        run_store: SQLAlchemyRunStore | None = None,
    ) -> None:
        self.api_key = api_key or ""
        self.api_secret = api_secret or ""
        self.access_token = access_token or ""
        self.run_store = run_store

    def login_url(self) -> str | None:
        if not self.api_key:
            return None
        return f"https://kite.zerodha.com/connect/login?v=3&api_key={quote_plus(self.api_key)}"

    def is_connected(self) -> bool:
        return bool(self._active_access_token())

    def current_session(self) -> BrokerAuthSession | None:
        if self.run_store:
            session = self.run_store.get_broker_session(BrokerName.ZERODHA)
            if session:
                return session
        if not self.access_token:
            return None
        return BrokerAuthSession(
            broker=BrokerName.ZERODHA,
            access_token=self.access_token,
            api_key=self.api_key,
            received_at=utcnow(),
        )

    async def exchange_request_token(
        self, request_token: str, actor_operator_id: str | None = None
    ) -> BrokerAuthSession:
        if not (self.api_key and self.api_secret):
            raise RuntimeError("Zerodha API credentials are not configured.")
        checksum = hashlib.sha256(
            f"{self.api_key}{request_token}{self.api_secret}".encode()
        ).hexdigest()
        headers = {"X-Kite-Version": "3", "Accept": "application/json"}
        data = {
            "api_key": self.api_key,
            "request_token": request_token,
            "checksum": checksum,
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://api.kite.trade/session/token", data=data, headers=headers
            )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "success":
            raise RuntimeError(payload.get("message") or "Zerodha token exchange failed.")
        data_payload = payload.get("data") or {}
        session = BrokerAuthSession(
            broker=BrokerName.ZERODHA,
            request_token=request_token,
            access_token=str(data_payload.get("access_token") or ""),
            refresh_token=data_payload.get("refresh_token"),
            public_token=data_payload.get("public_token"),
            api_key=self.api_key,
            user_id=data_payload.get("user_id"),
            user_name=data_payload.get("user_name"),
            email=data_payload.get("email"),
            login_time=data_payload.get("login_time"),
            actor_operator_id=actor_operator_id,
            received_at=utcnow(),
            raw=data_payload,
        )
        self.access_token = session.access_token
        if self.run_store:
            self.run_store.save_broker_session(session)
        return session

    def disconnect(self) -> None:
        self.access_token = ""
        if self.run_store:
            self.run_store.delete_broker_session(BrokerName.ZERODHA)

    async def preview_order(self, order_request: OrderRequest) -> OrderPreview:
        price = order_request.limit_price or order_request.stop_price or 0.0
        warnings = []
        if not self.is_connected():
            warnings.append("Zerodha is not connected.")
        warnings.append("Non-paper execution still requires explicit human approval.")
        return OrderPreview(
            recommendation_id=order_request.recommendation_id,
            broker=order_request.broker,
            action=order_request.action,
            symbol=order_request.symbol,
            quantity=order_request.quantity,
            order_type=order_request.order_type,
            estimated_notional=order_request.quantity * price,
            warnings=warnings,
        )

    async def submit_order(self, order_request: OrderRequest) -> ExecutionResult:
        access_token = self._active_access_token()
        if not (self.api_key and access_token):
            return ExecutionResult(
                recommendation_id=order_request.recommendation_id,
                broker=order_request.broker,
                status="REJECTED",
                message="Zerodha credentials are not configured.",
            )
        if order_request.action == Action.HOLD:
            return ExecutionResult(
                recommendation_id=order_request.recommendation_id,
                broker=order_request.broker,
                status="REJECTED",
                message="Cannot submit a HOLD recommendation as a live order.",
            )
        order_type = self._map_order_type(order_request.order_type)
        data = {
            "tradingsymbol": order_request.symbol,
            "exchange": str(order_request.metadata.get("exchange") or "NSE"),
            "transaction_type": order_request.action.value,
            "order_type": order_type,
            "quantity": order_request.quantity,
            "product": str(order_request.metadata.get("product") or "CNC"),
            "validity": str(order_request.metadata.get("validity") or "DAY"),
            "variety": str(order_request.metadata.get("variety") or "regular"),
        }
        if order_type in {"LIMIT", "SL"} and order_request.limit_price is not None:
            data["price"] = order_request.limit_price
        if order_type == "SL" and order_request.stop_price is not None:
            data["trigger_price"] = order_request.stop_price
        headers = {
            "X-Kite-Version": "3",
            "Authorization": f"token {self.api_key}:{access_token}",
            "Accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"https://api.kite.trade/orders/{data.pop('variety')}",
                    data=data,
                    headers=headers,
                )
            response.raise_for_status()
            payload = response.json()
            if payload.get("status") != "success":
                return ExecutionResult(
                    recommendation_id=order_request.recommendation_id,
                    broker=order_request.broker,
                    status="FAILED",
                    message=payload.get("message") or "Zerodha order submission failed.",
                )
            order_id = (payload.get("data") or {}).get("order_id")
            return ExecutionResult(
                recommendation_id=order_request.recommendation_id,
                broker=order_request.broker,
                status="PENDING",
                message="Zerodha order submitted successfully.",
                broker_order_id=order_id,
            )
        except httpx.HTTPError as exc:
            return ExecutionResult(
                recommendation_id=order_request.recommendation_id,
                broker=order_request.broker,
                status="FAILED",
                message=f"Zerodha order submission failed: {exc}",
            )

    async def get_positions(self) -> list[Position]:
        access_token = self._active_access_token()
        if not (self.api_key and access_token):
            return []
        headers = {
            "X-Kite-Version": "3",
            "Authorization": f"token {self.api_key}:{access_token}",
            "Accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    "https://api.kite.trade/portfolio/positions", headers=headers
                )
            response.raise_for_status()
        except httpx.HTTPError:
            return []
        payload = response.json().get("data", {})
        return [
            Position(
                symbol=item.get("tradingsymbol") or "UNKNOWN",
                quantity=int(item.get("quantity") or 0),
                average_price=float(item.get("average_price") or 0.0),
                market_price=float(item.get("last_price") or 0.0),
                unrealized_pnl=float(item.get("pnl") or 0.0),
                broker_account_id=item.get("instrument_token"),
            )
            for item in payload.get("net", [])
        ]

    def _active_access_token(self) -> str:
        session = self.current_session()
        if session and session.access_token:
            return session.access_token
        return self.access_token

    @staticmethod
    def _map_order_type(order_type: OrderType) -> str:
        if order_type == OrderType.STOP:
            return "SL"
        return order_type.value
