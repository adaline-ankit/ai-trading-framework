from __future__ import annotations

from ai_trading_framework.analytics.benchmark import BenchmarkService
from ai_trading_framework.core.approvals.service import ApprovalService
from ai_trading_framework.core.engine.workflow import WorkflowEngine
from ai_trading_framework.core.replay.service import ReplayEngine
from ai_trading_framework.models import (
    BrokerName,
    MarketContext,
    Recommendation,
    RiskEvaluation,
    RunRecord,
)
from ai_trading_framework.storage.sqlalchemy.repository import SQLAlchemyRunStore


class OperatorRuntime:
    def __init__(
        self,
        workflow: WorkflowEngine,
        approval_service: ApprovalService,
        replay_engine: ReplayEngine,
        benchmark_service: BenchmarkService,
        run_store: SQLAlchemyRunStore,
        notifier=None,
    ) -> None:
        self.workflow = workflow
        self.approval_service = approval_service
        self.replay_engine = replay_engine
        self.benchmark_service = benchmark_service
        self.run_store = run_store
        self.notifier = notifier

    async def analyze(
        self,
        context: MarketContext,
        recommendations: list[Recommendation],
        broker: BrokerName,
        simulate_approval: bool = False,
    ) -> tuple[RunRecord, list[Recommendation], list[RiskEvaluation]]:
        run, recommendations, risks = await self.workflow.process(
            context, recommendations, broker, simulate_approval=simulate_approval
        )
        self.run_store.save(run)
        if self.notifier and recommendations:
            approval = self.approval_service.get(recommendations[0].recommendation_id)
            await self.notifier.send_recommendation(
                recommendations[0], approval.token if approval else None
            )
        return run, recommendations, risks

    def replay(self, run_id: str) -> dict[str, object] | None:
        run = self.run_store.get(run_id)
        if not run:
            return None
        return self.replay_engine.replay(run)
