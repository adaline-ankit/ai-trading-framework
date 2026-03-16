from __future__ import annotations

import csv
import hashlib
from datetime import date
from io import StringIO
from urllib.parse import quote_plus

import httpx

from ai_trading_framework.brokers.base import BaseBrokerClient
from ai_trading_framework.models import (
    Action,
    AssetClass,
    BrokerAuthSession,
    BrokerCapabilities,
    BrokerName,
    BrokerProduct,
    ExecutionResult,
    InstrumentDescriptor,
    OrderPreview,
    OrderRequest,
    OrderType,
    Position,
    utcnow,
)
from ai_trading_framework.storage.sqlalchemy.repository import SQLAlchemyRunStore


class ZerodhaBrokerClient(BaseBrokerClient):
    capabilities = BrokerCapabilities(
        supports_intraday=True,
        supports_websocket=True,
        supports_holdings=True,
        supports_instruments_master=True,
        supports_options=True,
        supports_equities=True,
        supports_etfs=True,
        supports_futures=True,
        supports_commodities=True,
        supports_currency=True,
        supports_mutual_funds=True,
    )

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
        if (
            order_request.instrument
            and order_request.instrument.asset_class == AssetClass.MUTUAL_FUND
        ):
            warnings.append(
                "Coin mutual funds are exposed in the framework, but direct order submission "
                "is not enabled in this runtime."
            )
        warnings.append("Non-paper execution still requires explicit human approval.")
        return OrderPreview(
            recommendation_id=order_request.recommendation_id,
            broker=order_request.broker,
            action=order_request.action,
            symbol=order_request.symbol,
            instrument=order_request.instrument,
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
        if (
            order_request.instrument
            and order_request.instrument.asset_class == AssetClass.MUTUAL_FUND
        ):
            return ExecutionResult(
                recommendation_id=order_request.recommendation_id,
                broker=order_request.broker,
                status="REJECTED",
                message=(
                    "Zerodha mutual fund order submission is not enabled in this runtime. "
                    "Use the framework for discovery, holdings, approvals, and workflow automation."
                ),
            )
        order_type = self._map_order_type(order_request.order_type)
        data = {
            "tradingsymbol": order_request.instrument.tradingsymbol
            if order_request.instrument and order_request.instrument.tradingsymbol
            else order_request.symbol,
            "exchange": str(
                order_request.metadata.get("exchange")
                or (order_request.instrument.exchange if order_request.instrument else None)
                or "NSE"
            ),
            "transaction_type": order_request.action.value,
            "order_type": order_type,
            "quantity": order_request.quantity,
            "product": str(order_request.product.value),
            "validity": str(order_request.metadata.get("validity") or "DAY"),
            "variety": str(order_request.variety.value),
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
                quantity=float(item.get("quantity") or 0),
                average_price=float(item.get("average_price") or 0.0),
                market_price=float(item.get("last_price") or 0.0),
                unrealized_pnl=float(item.get("pnl") or 0.0),
                broker_account_id=item.get("instrument_token"),
                asset_class=self._asset_class_from_fields(
                    segment=item.get("exchange"),
                    instrument_type=item.get("instrument_type"),
                    tradingsymbol=item.get("tradingsymbol"),
                ),
                product=item.get("product"),
                instrument=InstrumentDescriptor(
                    broker=BrokerName.ZERODHA,
                    symbol=item.get("tradingsymbol") or "UNKNOWN",
                    tradingsymbol=item.get("tradingsymbol"),
                    exchange=item.get("exchange"),
                    segment=item.get("exchange"),
                    asset_class=self._asset_class_from_fields(
                        segment=item.get("exchange"),
                        instrument_type=item.get("instrument_type"),
                        tradingsymbol=item.get("tradingsymbol"),
                    ),
                    instrument_type=item.get("instrument_type"),
                    instrument_token=str(item.get("instrument_token"))
                    if item.get("instrument_token") is not None
                    else None,
                ),
            )
            for item in payload.get("net", [])
        ]

    async def get_holdings(self) -> list[Position]:
        access_token = self._active_access_token()
        if not (self.api_key and access_token):
            return []
        headers = self._headers(access_token)
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    "https://api.kite.trade/portfolio/holdings", headers=headers
                )
            response.raise_for_status()
        except httpx.HTTPError:
            return []
        payload = response.json().get("data", [])
        return [
            Position(
                symbol=item.get("tradingsymbol") or "UNKNOWN",
                quantity=float(item.get("quantity") or 0),
                average_price=float(item.get("average_price") or 0.0),
                market_price=float(item.get("last_price") or 0.0),
                unrealized_pnl=float(item.get("pnl") or 0.0),
                broker_account_id=str(item.get("instrument_token"))
                if item.get("instrument_token") is not None
                else None,
                asset_class=self._asset_class_from_fields(
                    segment=item.get("exchange"),
                    instrument_type=item.get("instrument_type"),
                    tradingsymbol=item.get("tradingsymbol"),
                ),
                product=BrokerProduct.CNC.value,
                instrument=InstrumentDescriptor(
                    broker=BrokerName.ZERODHA,
                    symbol=item.get("tradingsymbol") or "UNKNOWN",
                    tradingsymbol=item.get("tradingsymbol"),
                    exchange=item.get("exchange"),
                    segment=item.get("exchange"),
                    asset_class=self._asset_class_from_fields(
                        segment=item.get("exchange"),
                        instrument_type=item.get("instrument_type"),
                        tradingsymbol=item.get("tradingsymbol"),
                    ),
                    instrument_type=item.get("instrument_type"),
                    instrument_token=str(item.get("instrument_token"))
                    if item.get("instrument_token") is not None
                    else None,
                    isin=item.get("isin"),
                ),
            )
            for item in payload
        ]

    async def get_mutual_fund_holdings(self) -> list[Position]:
        access_token = self._active_access_token()
        if not (self.api_key and access_token):
            return []
        headers = self._headers(access_token)
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get("https://api.kite.trade/mf/holdings", headers=headers)
            response.raise_for_status()
        except httpx.HTTPError:
            return []
        payload = response.json().get("data", [])
        return [
            Position(
                symbol=item.get("tradingsymbol") or item.get("fund") or "UNKNOWN",
                quantity=float(item.get("quantity") or 0),
                average_price=float(item.get("average_price") or 0.0),
                market_price=float(item.get("last_price") or item.get("average_price") or 0.0),
                unrealized_pnl=float(item.get("pnl") or 0.0),
                broker_account_id=item.get("folio"),
                asset_class=AssetClass.MUTUAL_FUND,
                product=BrokerProduct.COIN.value,
                instrument=InstrumentDescriptor(
                    broker=BrokerName.ZERODHA,
                    symbol=item.get("tradingsymbol") or item.get("fund") or "UNKNOWN",
                    tradingsymbol=item.get("tradingsymbol") or item.get("fund"),
                    name=item.get("fund"),
                    exchange="MF",
                    segment="MF",
                    asset_class=AssetClass.MUTUAL_FUND,
                    instrument_token=item.get("tradingsymbol"),
                    minimum_purchase_amount=float(item.get("minimum_purchase_amount") or 0.0)
                    if item.get("minimum_purchase_amount") is not None
                    else None,
                ),
            )
            for item in payload
        ]

    async def list_instruments(
        self,
        query: str | None = None,
        exchange: str | None = None,
        segment: str | None = None,
        limit: int = 200,
    ) -> list[InstrumentDescriptor]:
        rows = await self._fetch_csv(
            f"https://api.kite.trade/instruments/{exchange}"
            if exchange
            else "https://api.kite.trade/instruments"
        )
        instruments = [self._instrument_from_csv_row(row) for row in rows]
        return self._filter_instruments(instruments, query=query, segment=segment, limit=limit)

    async def list_mutual_funds(
        self,
        query: str | None = None,
        limit: int = 200,
    ) -> list[InstrumentDescriptor]:
        rows = await self._fetch_csv("https://api.kite.trade/mf/instruments")
        instruments = [self._mf_instrument_from_csv_row(row) for row in rows]
        return self._filter_instruments(instruments, query=query, segment="MF", limit=limit)

    def _active_access_token(self) -> str:
        session = self.current_session()
        if session and session.access_token:
            return session.access_token
        return self.access_token

    def _headers(self, access_token: str) -> dict[str, str]:
        return {
            "X-Kite-Version": "3",
            "Authorization": f"token {self.api_key}:{access_token}",
            "Accept": "application/json",
        }

    @staticmethod
    def _map_order_type(order_type: OrderType) -> str:
        if order_type == OrderType.STOP:
            return "SL"
        return order_type.value

    async def _fetch_csv(self, url: str) -> list[dict[str, str]]:
        access_token = self._active_access_token()
        if not (self.api_key and access_token):
            return []
        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.get(url, headers=self._headers(access_token))
        response.raise_for_status()
        reader = csv.DictReader(StringIO(response.text))
        return [dict(row) for row in reader]

    @staticmethod
    def _filter_instruments(
        instruments: list[InstrumentDescriptor],
        *,
        query: str | None,
        segment: str | None,
        limit: int,
    ) -> list[InstrumentDescriptor]:
        filtered = instruments
        if segment:
            segment_upper = segment.upper()
            filtered = [item for item in filtered if (item.segment or "").upper() == segment_upper]
        if query:
            query_upper = query.upper()
            filtered = [
                item
                for item in filtered
                if query_upper in item.symbol.upper()
                or query_upper in (item.tradingsymbol or "").upper()
                or query_upper in (item.name or "").upper()
            ]
        return filtered[:limit]

    @classmethod
    def _instrument_from_csv_row(cls, row: dict[str, str]) -> InstrumentDescriptor:
        tradingsymbol = row.get("tradingsymbol") or row.get("symbol") or "UNKNOWN"
        exchange = row.get("exchange") or row.get("segment")
        segment = row.get("segment") or exchange
        instrument_type = row.get("instrument_type") or None
        return InstrumentDescriptor(
            broker=BrokerName.ZERODHA,
            symbol=tradingsymbol,
            tradingsymbol=tradingsymbol,
            name=row.get("name") or None,
            exchange=exchange,
            segment=segment,
            asset_class=cls._asset_class_from_fields(
                segment=segment,
                instrument_type=instrument_type,
                tradingsymbol=tradingsymbol,
            ),
            instrument_type=instrument_type,
            instrument_token=row.get("instrument_token") or None,
            exchange_token=row.get("exchange_token") or None,
            isin=row.get("isin") or None,
            expiry=cls._parse_date(row.get("expiry") or None),
            strike=float(row["strike"]) if row.get("strike") not in {None, ""} else None,
            lot_size=int(float(row["lot_size"])) if row.get("lot_size") not in {None, ""} else None,
            tick_size=float(row["tick_size"]) if row.get("tick_size") not in {None, ""} else None,
            metadata=row,
        )

    @classmethod
    def _mf_instrument_from_csv_row(cls, row: dict[str, str]) -> InstrumentDescriptor:
        tradingsymbol = row.get("tradingsymbol") or row.get("symbol") or row.get("fund") or "MF"
        minimum_purchase_amount = None
        for key in ("minimum_purchase_amount", "minimum_additional_purchase_amount"):
            if row.get(key) not in {None, ""}:
                minimum_purchase_amount = float(row[key])
                break
        return InstrumentDescriptor(
            broker=BrokerName.ZERODHA,
            symbol=tradingsymbol,
            tradingsymbol=tradingsymbol,
            name=row.get("fund") or row.get("name") or tradingsymbol,
            exchange="MF",
            segment="MF",
            asset_class=AssetClass.MUTUAL_FUND,
            instrument_type="MF",
            isin=row.get("isin") or None,
            minimum_purchase_amount=minimum_purchase_amount,
            metadata=row,
        )

    @staticmethod
    def _asset_class_from_fields(
        *,
        segment: str | None,
        instrument_type: str | None,
        tradingsymbol: str | None,
    ) -> AssetClass:
        segment_upper = (segment or "").upper()
        instrument_upper = (instrument_type or "").upper()
        tradingsymbol_upper = (tradingsymbol or "").upper()
        if segment_upper == "MF" or instrument_upper == "MF":
            return AssetClass.MUTUAL_FUND
        if segment_upper in {"MCX", "BCD", "MCXFO"}:
            return AssetClass.COMMODITY
        if segment_upper in {"CDS", "BCD"}:
            return AssetClass.CURRENCY
        if instrument_upper in {"FUT", "FUTSTK", "FUTIDX"}:
            return AssetClass.FUTURE
        if instrument_upper in {"CE", "PE", "OPT", "OPTSTK", "OPTIDX"}:
            return AssetClass.OPTION
        if instrument_upper == "ETF" or tradingsymbol_upper.endswith("ETF"):
            return AssetClass.ETF
        if instrument_upper == "INDEX":
            return AssetClass.INDEX
        if segment_upper in {"NSE", "BSE", "NFO"}:
            return AssetClass.EQUITY
        return AssetClass.UNKNOWN

    @staticmethod
    def _parse_date(value: str | None) -> date | None:
        if not value:
            return None
        return date.fromisoformat(value)
