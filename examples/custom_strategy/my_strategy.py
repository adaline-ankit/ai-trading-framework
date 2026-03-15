from ai_trading_framework.models import Action, Recommendation, Signal
from ai_trading_framework.sdk.strategies import TradingStrategy


class MyStrategy(TradingStrategy):
    name = "my_strategy"

    async def scan(self, market_context):
        return [
            Signal(
                symbol=market_context.symbol,
                strategy_name=self.name,
                action=Action.BUY,
                confidence=0.68,
                rationale="Custom strategy sees favorable structure.",
            )
        ]

    async def analyze(self, signal, context) -> Recommendation | None:
        return None
