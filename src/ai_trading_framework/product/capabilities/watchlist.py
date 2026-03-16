from __future__ import annotations

from ai_trading_framework.product.state import WatchlistState


class WatchlistCapability:
    def __init__(self, state: WatchlistState) -> None:
        self.state = state

    def get_all(self) -> list[str]:
        return self.state.get_all()

    def add(self, symbol: str) -> list[str]:
        return self.state.add(symbol)

    def remove(self, symbol: str) -> list[str]:
        return self.state.remove(symbol)
