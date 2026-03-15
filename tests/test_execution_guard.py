import pytest

from ai_trading_framework.brokers.paper import PaperBrokerClient
from ai_trading_framework.core.approvals import ApprovalService
from ai_trading_framework.data.providers.demo import DemoMarketDataProvider
from ai_trading_framework.execution import ExecutionService
from ai_trading_framework.models import (
    Action,
    BrokerName,
    OrderRequest,
    Recommendation,
    RiskDecision,
)


@pytest.mark.asyncio
async def test_live_execution_requires_approval_token():
    approval_service = ApprovalService()
    execution = ExecutionService(
        approval_service,
        {
            BrokerName.PAPER: PaperBrokerClient(DemoMarketDataProvider()),
        },
    )
    recommendation = Recommendation(
        symbol="INFY",
        action=Action.BUY,
        confidence=0.8,
        thesis="Momentum looks favorable.",
        strategy_name="momentum_strategy",
    )
    result = await execution.execute(
        recommendation,
        OrderRequest(
            recommendation_id=recommendation.recommendation_id,
            symbol="INFY",
            broker=BrokerName.PAPER,
            action=Action.BUY,
            quantity=1,
        ),
        RiskDecision.APPROVED,
    )
    assert result.status == "FILLED"
