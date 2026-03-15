from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from ai_trading_framework.models import (
    BrokerCapabilities,
    EvaluatedSignal,
    ExecutionResult,
    MarketContext,
    OrderPreview,
    OrderRequest,
    PortfolioState,
    Recommendation,
    RiskEvaluation,
    Signal,
)

SignalBatchItem = Signal | EvaluatedSignal


class StrategyProvider(ABC):
    @abstractmethod
    async def generate_signals(self, market_context: MarketContext) -> list[Signal]: ...


class SignalEngine(ABC):
    @abstractmethod
    async def evaluate(
        self,
        signals: Sequence[SignalBatchItem],
        market_context: MarketContext,
    ) -> list[EvaluatedSignal]: ...


class ReasoningEngine(ABC):
    @abstractmethod
    async def analyze(
        self,
        evaluated_signal: EvaluatedSignal,
        market_context: MarketContext,
    ) -> Recommendation: ...


class RiskPolicy(ABC):
    policy_name: str = "risk_policy"

    @abstractmethod
    async def validate(
        self,
        recommendation: Recommendation,
        portfolio_state: PortfolioState,
        market_context: MarketContext,
    ) -> RiskEvaluation: ...


class BrokerClient(ABC):
    capabilities = BrokerCapabilities()

    @abstractmethod
    async def preview_order(self, order_request: OrderRequest) -> OrderPreview: ...

    @abstractmethod
    async def submit_order(self, order_request: OrderRequest) -> ExecutionResult: ...

    @abstractmethod
    async def get_positions(self) -> list[Any]: ...


class ExecutionPolicy(ABC):
    @abstractmethod
    async def execute(
        self, recommendation: Recommendation, order_request: OrderRequest
    ) -> ExecutionResult: ...


class Notifier(ABC):
    @abstractmethod
    async def send_alert(self, message: str) -> None: ...


class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str) -> str: ...
