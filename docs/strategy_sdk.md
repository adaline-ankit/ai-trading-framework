# Strategy SDK

Create a single-file strategy by subclassing `TradingStrategy`:

```python
from ai_trading_framework.models import Action, Signal
from ai_trading_framework.sdk.strategies import TradingStrategy

class MyStrategy(TradingStrategy):
    name = "my_strategy"

    async def scan(self, market_context):
        return [
            Signal(
                symbol=market_context.symbol,
                strategy_name=self.name,
                action=Action.BUY,
                confidence=0.7,
                rationale="Custom thesis",
            )
        ]

    async def analyze(self, signal, context):
        return None
```
