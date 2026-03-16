from __future__ import annotations

from ai_trading_framework.core.runtime.operator import OperatorRuntime
from ai_trading_framework.models import BrokerName


class PortfolioCapability:
    def __init__(self, runtime: OperatorRuntime) -> None:
        self.runtime = runtime

    async def summary(self, broker: BrokerName) -> dict[str, object]:
        positions = [
            position.model_dump(mode="json")
            for position in await self.runtime.get_positions(broker)
        ]
        holdings = [
            position.model_dump(mode="json") for position in await self.runtime.get_holdings(broker)
        ]
        return {
            "broker": broker.value,
            "positions": positions,
            "holdings": holdings,
        }
