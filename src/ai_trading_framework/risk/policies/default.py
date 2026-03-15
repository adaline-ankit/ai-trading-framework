from __future__ import annotations

from ai_trading_framework.core.plugin_system.interfaces import RiskPolicy
from ai_trading_framework.models import (
    MarketContext,
    PortfolioState,
    Recommendation,
    RiskCheckResult,
    RiskDecision,
    RiskEvaluation,
)


class BaseSimplePolicy(RiskPolicy):
    policy_name = "base"

    async def validate(
        self,
        recommendation: Recommendation,
        portfolio_state: PortfolioState,
        market_context: MarketContext,
    ) -> RiskEvaluation:
        raise NotImplementedError

    def _evaluation(
        self, decision: RiskDecision, reasons: list[str], max_position_size: int | None = None
    ) -> RiskEvaluation:
        return RiskEvaluation(
            decision=decision,
            summary=reasons[0] if reasons else f"{self.policy_name} passed.",
            checks=[
                RiskCheckResult(policy_name=self.policy_name, decision=decision, reasons=reasons)
            ],
            max_position_size=max_position_size,
        )


class MinConfidencePolicy(BaseSimplePolicy):
    policy_name = "min_confidence"

    def __init__(self, threshold: float = 0.55) -> None:
        self.threshold = threshold

    async def validate(
        self,
        recommendation: Recommendation,
        portfolio_state: PortfolioState,
        market_context: MarketContext,
    ) -> RiskEvaluation:
        if recommendation.action.value != "HOLD" and recommendation.confidence < self.threshold:
            return self._evaluation(
                RiskDecision.REJECTED,
                [
                    "Confidence "
                    f"{recommendation.confidence:.2f} below threshold "
                    f"{self.threshold:.2f}."
                ],
            )
        return self._evaluation(RiskDecision.APPROVED, ["Confidence policy passed."])


class MaxPositionsPolicy(BaseSimplePolicy):
    policy_name = "max_positions"

    def __init__(self, max_positions: int = 12) -> None:
        self.max_positions = max_positions

    async def validate(
        self,
        recommendation: Recommendation,
        portfolio_state: PortfolioState,
        market_context: MarketContext,
    ) -> RiskEvaluation:
        if (
            recommendation.action.value == "BUY"
            and len(portfolio_state.positions) >= self.max_positions
        ):
            return self._evaluation(RiskDecision.REJECTED, ["Maximum open position count reached."])
        return self._evaluation(RiskDecision.APPROVED, ["Open position count policy passed."])


class MaxCapitalPerTradePolicy(BaseSimplePolicy):
    policy_name = "max_capital_per_trade"

    def __init__(self, max_capital: float = 250_000.0) -> None:
        self.max_capital = max_capital

    async def validate(
        self,
        recommendation: Recommendation,
        portfolio_state: PortfolioState,
        market_context: MarketContext,
    ) -> RiskEvaluation:
        price = recommendation.entry_price or market_context.price.price
        max_position_size = max(int(self.max_capital / max(price, 1.0)), 1)
        return self._evaluation(
            RiskDecision.APPROVED,
            ["Capital-per-trade policy passed."],
            max_position_size=max_position_size,
        )


class MaxDailyLossPolicy(BaseSimplePolicy):
    policy_name = "max_daily_loss"

    def __init__(self, max_daily_loss: float = 50_000.0) -> None:
        self.max_daily_loss = max_daily_loss

    async def validate(
        self,
        recommendation: Recommendation,
        portfolio_state: PortfolioState,
        market_context: MarketContext,
    ) -> RiskEvaluation:
        if portfolio_state.daily_pnl <= -self.max_daily_loss:
            return self._evaluation(RiskDecision.REJECTED, ["Daily loss limit exceeded."])
        return self._evaluation(RiskDecision.APPROVED, ["Daily loss policy passed."])


class MaxSymbolExposurePolicy(BaseSimplePolicy):
    policy_name = "max_symbol_exposure"

    def __init__(self, max_exposure: float = 0.2) -> None:
        self.max_exposure = max_exposure

    async def validate(
        self,
        recommendation: Recommendation,
        portfolio_state: PortfolioState,
        market_context: MarketContext,
    ) -> RiskEvaluation:
        total = max(
            portfolio_state.cash_available
            + sum(pos.market_price * pos.quantity for pos in portfolio_state.positions),
            1.0,
        )
        symbol_exposure = sum(
            pos.market_price * pos.quantity
            for pos in portfolio_state.positions
            if pos.symbol == recommendation.symbol
        )
        if symbol_exposure / total > self.max_exposure:
            return self._evaluation(
                RiskDecision.REJECTED, ["Symbol exposure exceeds configured limit."]
            )
        return self._evaluation(RiskDecision.APPROVED, ["Symbol exposure policy passed."])


class RestrictedSymbolsPolicy(BaseSimplePolicy):
    policy_name = "restricted_symbols"

    def __init__(self, restricted: set[str] | None = None) -> None:
        self.restricted = {symbol.upper() for symbol in (restricted or set())}

    async def validate(
        self,
        recommendation: Recommendation,
        portfolio_state: PortfolioState,
        market_context: MarketContext,
    ) -> RiskEvaluation:
        if recommendation.symbol.upper() in self.restricted:
            return self._evaluation(RiskDecision.REJECTED, ["Symbol is restricted."])
        return self._evaluation(RiskDecision.APPROVED, ["Restricted symbol policy passed."])


class LiquidityPolicy(BaseSimplePolicy):
    policy_name = "liquidity_checks"

    def __init__(self, min_volume: int = 100_000) -> None:
        self.min_volume = min_volume

    async def validate(
        self,
        recommendation: Recommendation,
        portfolio_state: PortfolioState,
        market_context: MarketContext,
    ) -> RiskEvaluation:
        if market_context.price.volume < self.min_volume:
            return self._evaluation(RiskDecision.REJECTED, ["Volume below liquidity threshold."])
        return self._evaluation(RiskDecision.APPROVED, ["Liquidity policy passed."])


class SpreadPolicy(BaseSimplePolicy):
    policy_name = "spread_checks"

    def __init__(self, max_spread_percent: float = 0.015) -> None:
        self.max_spread_percent = max_spread_percent

    async def validate(
        self,
        recommendation: Recommendation,
        portfolio_state: PortfolioState,
        market_context: MarketContext,
    ) -> RiskEvaluation:
        spread = float(market_context.metadata.get("spread_percent", 0.004))
        if spread > self.max_spread_percent:
            return self._evaluation(RiskDecision.REJECTED, ["Spread exceeds configured threshold."])
        return self._evaluation(RiskDecision.APPROVED, ["Spread policy passed."])
