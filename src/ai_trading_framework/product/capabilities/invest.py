from __future__ import annotations

from ai_trading_framework.analytics.investment_planner import InvestmentPlanner
from ai_trading_framework.models import BrokerName, InvestmentPlan
from ai_trading_framework.product.config import BotConfig
from ai_trading_framework.product.state import WatchlistState


class InvestmentCapability:
    def __init__(
        self,
        planner: InvestmentPlanner,
        watchlist_state: WatchlistState,
        config: BotConfig,
    ) -> None:
        self.planner = planner
        self.watchlist_state = watchlist_state
        self.config = config

    async def plan(
        self,
        *,
        budget: float | None,
        symbols: list[str] | None,
        broker: BrokerName,
        available_cash: float | None = None,
    ) -> InvestmentPlan:
        effective_budget = budget
        if effective_budget is None:
            if self.config.broker_settings.auto_budget_mode and available_cash:
                effective_budget = available_cash
            else:
                effective_budget = self.config.defaults.default_budget
        return await self.planner.plan(
            budget=effective_budget,
            symbols=symbols or self.watchlist_state.get_all(),
            broker=broker,
        )
