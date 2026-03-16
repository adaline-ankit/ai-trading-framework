from __future__ import annotations

from ai_trading_framework.storage.sqlalchemy.repository import SQLAlchemyRunStore


class WatchlistState:
    namespace = "product"
    key = "watchlist"

    def __init__(self, store: SQLAlchemyRunStore, default_symbols: list[str] | None = None) -> None:
        self.store = store
        self.default_symbols = [symbol.upper() for symbol in (default_symbols or [])]

    def get_all(self) -> list[str]:
        stored = self.store.get_state(self.namespace, self.key, default=self.default_symbols) or []
        return [str(symbol).upper() for symbol in stored]

    def add(self, symbol: str) -> list[str]:
        symbols = self.get_all()
        normalized = symbol.upper()
        if normalized not in symbols:
            symbols.append(normalized)
        self.store.set_state(self.namespace, self.key, symbols)
        return symbols

    def remove(self, symbol: str) -> list[str]:
        normalized = symbol.upper()
        symbols = [item for item in self.get_all() if item != normalized]
        self.store.set_state(self.namespace, self.key, symbols)
        return symbols

    def replace(self, symbols: list[str]) -> list[str]:
        normalized = [symbol.upper() for symbol in symbols]
        self.store.set_state(self.namespace, self.key, normalized)
        return normalized
