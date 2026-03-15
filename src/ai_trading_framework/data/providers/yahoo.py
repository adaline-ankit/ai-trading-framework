from __future__ import annotations

from datetime import UTC, datetime

import httpx

from ai_trading_framework.data.providers.base import MarketDataProvider
from ai_trading_framework.models import Candle, PriceSnapshot


class YahooMarketDataProvider(MarketDataProvider):
    base_url = "https://query1.finance.yahoo.com"

    def _symbol(self, symbol: str) -> str:
        if "." in symbol:
            return symbol
        return f"{symbol.upper()}.NS"

    async def get_price(self, symbol: str) -> PriceSnapshot:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.base_url}/v8/finance/chart/{self._symbol(symbol)}",
                params={"interval": "1d", "range": "5d"},
            )
            response.raise_for_status()
        payload = response.json()["chart"]["result"][0]
        meta = payload["meta"]
        closes = payload["indicators"]["quote"][0]["close"]
        previous_close = meta.get("previousClose") or next(
            (price for price in reversed(closes[:-1]) if price), closes[-1]
        )
        last_price = meta.get("regularMarketPrice") or next(
            (price for price in reversed(closes) if price), previous_close
        )
        change_percent = (
            0.0 if not previous_close else ((last_price - previous_close) / previous_close) * 100
        )
        return PriceSnapshot(
            symbol=symbol.upper(),
            price=round(float(last_price), 2),
            change_percent=round(float(change_percent), 2),
            volume=int(payload["indicators"]["quote"][0]["volume"][-1] or 0),
            as_of=datetime.now(UTC),
        )

    async def get_ohlc(self, symbol: str, lookback_days: int) -> list[Candle]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"{self.base_url}/v8/finance/chart/{self._symbol(symbol)}",
                params={"interval": "1d", "range": f"{lookback_days}d"},
            )
            response.raise_for_status()
        result = response.json()["chart"]["result"][0]
        quote = result["indicators"]["quote"][0]
        candles: list[Candle] = []
        for index, timestamp in enumerate(result["timestamp"]):
            close = quote["close"][index]
            if close is None:
                continue
            candles.append(
                Candle(
                    timestamp=datetime.fromtimestamp(timestamp, tz=UTC),
                    open=float(quote["open"][index]),
                    high=float(quote["high"][index]),
                    low=float(quote["low"][index]),
                    close=float(close),
                    volume=int(quote["volume"][index] or 0),
                )
            )
        return candles
