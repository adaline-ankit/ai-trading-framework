from __future__ import annotations

from ai_trading_framework.core.runtime.operator import OperatorRuntime
from ai_trading_framework.models import BrokerName


class PortfolioCapability:
    def __init__(self, runtime: OperatorRuntime) -> None:
        self.runtime = runtime

    async def summary(self, broker: BrokerName) -> dict[str, object]:
        funds = await self.runtime.get_funds(broker)
        positions = [
            position.model_dump(mode="json")
            for position in await self.runtime.get_positions(broker)
        ]
        holdings = [
            position.model_dump(mode="json") for position in await self.runtime.get_holdings(broker)
        ]
        return {
            "broker": broker.value,
            "funds": funds.model_dump(mode="json") if funds else None,
            "positions": positions,
            "holdings": holdings,
            "position_count": len(positions),
            "holding_count": len(holdings),
        }
