from __future__ import annotations

from ai_trading_framework.analytics.benchmark import BenchmarkService
from ai_trading_framework.brokers.groww import GrowwBrokerClient
from ai_trading_framework.brokers.paper import PaperBrokerClient
from ai_trading_framework.brokers.zerodha import ZerodhaBrokerClient
from ai_trading_framework.core.approvals.service import ApprovalService
from ai_trading_framework.core.engine.workflow import WorkflowEngine
from ai_trading_framework.core.events.bus import EventBus
from ai_trading_framework.core.explainability.service import ExplainabilityEngine
from ai_trading_framework.core.observability.metrics import MetricsRegistry
from ai_trading_framework.core.plugin_system.registry import PluginRegistry
from ai_trading_framework.core.replay.service import ReplayEngine
from ai_trading_framework.core.runtime.operator import OperatorRuntime
from ai_trading_framework.core.runtime.settings import Settings
from ai_trading_framework.data.providers.demo import (
    DemoFundamentalProvider,
    DemoMarketDataProvider,
    DemoNewsProvider,
    DemoSentimentProvider,
)
from ai_trading_framework.execution.service import ExecutionService
from ai_trading_framework.models import BrokerName
from ai_trading_framework.notifiers.telegram import TelegramNotifier
from ai_trading_framework.reasoning.debate import DebateReasoningEngine
from ai_trading_framework.reasoning.llm import OpenAILLMProvider
from ai_trading_framework.risk.policies.base import RiskPolicyChain
from ai_trading_framework.risk.policies.default import (
    LiquidityPolicy,
    MaxCapitalPerTradePolicy,
    MaxDailyLossPolicy,
    MaxPositionsPolicy,
    MaxSymbolExposurePolicy,
    MinConfidencePolicy,
    RestrictedSymbolsPolicy,
    SpreadPolicy,
)
from ai_trading_framework.storage.sqlalchemy.repository import SQLAlchemyRunStore


class FrameworkBuilder:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.registry = PluginRegistry()
        self.event_bus = EventBus()
        self.metrics = MetricsRegistry()
        self.market_provider = DemoMarketDataProvider()
        self.news_provider = DemoNewsProvider()
        self.fundamental_provider = DemoFundamentalProvider()
        self.sentiment_provider = DemoSentimentProvider()
        self.reasoning_engine = DebateReasoningEngine(
            OpenAILLMProvider(settings.openai_api_key, settings.openai_reasoning_model)
        )
        self.notifier = TelegramNotifier(
            settings.telegram_bot_token, settings.telegram_default_chat_id
        )

    def with_market_provider(self, provider) -> FrameworkBuilder:
        self.market_provider = provider
        return self

    def with_reasoning_engine(self, engine) -> FrameworkBuilder:
        self.reasoning_engine = engine
        return self

    def build(self) -> OperatorRuntime:
        approval_service = ApprovalService()
        brokers = {
            BrokerName.PAPER: PaperBrokerClient(self.market_provider),
            BrokerName.ZERODHA: ZerodhaBrokerClient(
                self.settings.zerodha_api_key,
                self.settings.zerodha_api_secret,
                self.settings.zerodha_access_token,
            ),
            BrokerName.GROWW: GrowwBrokerClient(),
        }
        risk_chain = RiskPolicyChain(
            [
                MinConfidencePolicy(),
                MaxPositionsPolicy(),
                MaxCapitalPerTradePolicy(),
                MaxDailyLossPolicy(),
                MaxSymbolExposurePolicy(),
                RestrictedSymbolsPolicy(),
                LiquidityPolicy(),
                SpreadPolicy(),
            ]
        )
        execution_service = ExecutionService(approval_service, brokers)
        workflow = WorkflowEngine(
            event_bus=self.event_bus,
            explainability=ExplainabilityEngine(),
            approval_service=approval_service,
            risk_chain=risk_chain,
            execution_service=execution_service,
        )
        run_store = SQLAlchemyRunStore(self.settings.database_url)
        return OperatorRuntime(
            workflow=workflow,
            approval_service=approval_service,
            replay_engine=ReplayEngine(),
            benchmark_service=BenchmarkService(),
            run_store=run_store,
            notifier=self.notifier,
        )
