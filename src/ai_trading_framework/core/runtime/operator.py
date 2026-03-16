from __future__ import annotations

from collections.abc import Sequence
from html import escape

from ai_trading_framework.analytics.benchmark import BenchmarkService
from ai_trading_framework.core.approvals.service import ApprovalService
from ai_trading_framework.core.engine.workflow import WorkflowEngine
from ai_trading_framework.core.replay.service import ReplayEngine
from ai_trading_framework.core.security.auth import OperatorAuthService
from ai_trading_framework.models import (
    ApprovalRequest,
    ApprovalStatus,
    BrokerName,
    EventType,
    ExecutionResult,
    MarketContext,
    OrderPreview,
    OrderRequest,
    OrderType,
    Recommendation,
    RecommendationExplanation,
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
        auth_service: OperatorAuthService | None = None,
    ) -> None:
        self.workflow = workflow
        self.approval_service = approval_service
        self.replay_engine = replay_engine
        self.benchmark_service = benchmark_service
        self.run_store = run_store
        self.notifier = notifier
        self.auth_service = auth_service
        self.runs: dict[str, RunRecord] = {}
        self.recommendations: dict[str, Recommendation] = {}
        self.risks: dict[str, RiskEvaluation] = {}
        self.executions: dict[str, ExecutionResult] = {}
        self._bootstrap_from_store()

    async def analyze(
        self,
        context: MarketContext,
        recommendations: list[Recommendation],
        broker: BrokerName,
        simulate_approval: bool = False,
        notify: bool = True,
    ) -> tuple[RunRecord, list[Recommendation], list[RiskEvaluation]]:
        run, recommendations, risks = await self.workflow.process(
            context, recommendations, broker, simulate_approval=simulate_approval
        )
        self._store_run(run)
        for recommendation, risk in zip(recommendations, risks, strict=False):
            self.recommendations[recommendation.recommendation_id] = recommendation
            self.risks[recommendation.recommendation_id] = risk
        if notify and self.notifier and recommendations:
            approval = self.approval_service.get(recommendations[0].recommendation_id)
            await self.notifier.send_recommendation(
                recommendations[0], approval.token if approval else None
            )
        return run, recommendations, risks

    def replay(self, run_id: str) -> dict[str, object] | None:
        run = self.runs.get(run_id) or self.run_store.get(run_id)
        if not run:
            return None
        return self.replay_engine.replay(run)

    def list_recommendations(self) -> list[dict[str, object]]:
        recommendations = sorted(
            self.recommendations.values(),
            key=lambda recommendation: recommendation.run_id or "",
            reverse=True,
        )
        items: list[dict[str, object]] = []
        for recommendation in recommendations:
            approval = self.approval_service.get(recommendation.recommendation_id)
            risk = self.risks.get(recommendation.recommendation_id)
            execution = self.executions.get(recommendation.recommendation_id)
            items.append(
                {
                    "recommendation": recommendation.model_dump(mode="json"),
                    "risk": risk.model_dump(mode="json") if risk else None,
                    "approval": approval.model_dump(mode="json") if approval else None,
                    "execution": execution.model_dump(mode="json") if execution else None,
                }
            )
        return items

    def get_recommendation(self, identifier: str) -> Recommendation | None:
        if identifier in self.recommendations:
            return self.recommendations[identifier]
        candidates = [
            recommendation
            for recommendation in self.recommendations.values()
            if recommendation.symbol.upper() == identifier.upper()
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda recommendation: recommendation.run_id or "", reverse=True)
        return candidates[0]

    def get_risk(self, recommendation_id: str) -> RiskEvaluation | None:
        return self.risks.get(recommendation_id)

    def get_approval(self, recommendation_id: str) -> ApprovalRequest | None:
        return self.approval_service.get(recommendation_id)

    def clear_history(self) -> None:
        self.runs.clear()
        self.recommendations.clear()
        self.risks.clear()
        self.executions.clear()
        self.approval_service.clear()
        self.run_store.clear_runs()

    async def get_positions(self, broker: BrokerName):
        broker_client = self.workflow.execution_service.brokers[broker]
        return await broker_client.get_positions()

    async def get_holdings(self, broker: BrokerName):
        broker_client = self.workflow.execution_service.brokers[broker]
        return await broker_client.get_holdings()

    async def get_funds(self, broker: BrokerName):
        broker_client = self.workflow.execution_service.brokers[broker]
        return await broker_client.get_funds()

    def get_zerodha_client(self):
        return self.workflow.execution_service.brokers[BrokerName.ZERODHA]

    async def approve_recommendation(self, recommendation_id: str, token: str) -> ApprovalRequest:
        approval = self.approval_service.approve(recommendation_id, token)
        run = self._require_run(approval.run_id)
        await self.workflow.append_event(
            run, EventType.APPROVAL_GRANTED, approval.model_dump(mode="json")
        )
        self._store_run(run)
        recommendation = self.recommendations.get(recommendation_id)
        if self.notifier and recommendation:
            await self.notifier.send_alert(
                f"Approved {recommendation.symbol} ({recommendation.recommendation_id})."
            )
        return approval

    async def approve_with_stored_token(self, recommendation_id: str) -> ApprovalRequest:
        approval = self.get_approval(recommendation_id)
        if not approval:
            raise KeyError(f"Approval for {recommendation_id} not found.")
        return await self.approve_recommendation(recommendation_id, approval.token)

    async def reject_recommendation(self, recommendation_id: str, token: str) -> ApprovalRequest:
        approval = self.approval_service.reject(recommendation_id, token)
        run = self._require_run(approval.run_id)
        await self.workflow.append_event(
            run, EventType.APPROVAL_REJECTED, approval.model_dump(mode="json")
        )
        self._store_run(run)
        recommendation = self.recommendations.get(recommendation_id)
        if self.notifier and recommendation:
            await self.notifier.send_alert(
                f"Rejected {recommendation.symbol} ({recommendation.recommendation_id})."
            )
        return approval

    async def reject_with_stored_token(self, recommendation_id: str) -> ApprovalRequest:
        approval = self.get_approval(recommendation_id)
        if not approval:
            raise KeyError(f"Approval for {recommendation_id} not found.")
        return await self.reject_recommendation(recommendation_id, approval.token)

    async def preview_order(
        self,
        recommendation_id: str,
        broker: BrokerName,
        quantity: float,
        order_type: OrderType,
        limit_price: float | None = None,
        stop_price: float | None = None,
        approval_token: str | None = None,
    ) -> OrderPreview:
        recommendation = self._require_recommendation(recommendation_id)
        request = OrderRequest(
            recommendation_id=recommendation.recommendation_id,
            approval_token=approval_token,
            symbol=recommendation.symbol,
            instrument=recommendation.instrument,
            broker=broker,
            action=recommendation.action,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price or recommendation.entry_price,
            stop_price=stop_price or recommendation.stop_loss,
        )
        return await self.workflow.execution_service.preview_order(request)

    async def submit_order(
        self,
        recommendation_id: str,
        broker: BrokerName,
        quantity: float,
        order_type: OrderType,
        approval_token: str | None = None,
        limit_price: float | None = None,
        stop_price: float | None = None,
    ) -> tuple[OrderPreview, ExecutionResult]:
        recommendation = self._require_recommendation(recommendation_id)
        risk = self._require_risk(recommendation_id)
        run = self._require_run(recommendation.run_id)
        preview, result = await self.workflow.preview_and_execute(
            run=run,
            recommendation=recommendation,
            quantity=quantity,
            broker=broker,
            risk_evaluation=risk,
            order_type=order_type,
            approval_token=approval_token,
            limit_price=limit_price,
            stop_price=stop_price,
        )
        self.executions[recommendation_id] = result
        self._store_run(run)
        if self.notifier:
            await self.notifier.send_alert(
                f"Execution {result.status} for {recommendation.symbol}: {result.message}"
            )
        return preview, result

    async def handle_telegram_command(self, text: str, chat_id: str | None = None) -> str:
        parts = text.strip().split()
        if not parts:
            return "No command received."
        command = parts[0].lower()
        if command in {"/scan", "/analyze"}:
            if len(parts) < 2:
                return "Usage: /scan SYMBOL"
            symbol = parts[1].upper()
            recommendation = self.get_recommendation(symbol)
            if recommendation:
                response = self._format_recommendation(recommendation)
            else:
                response = (
                    f"No cached recommendation for {symbol}. "
                    "Use the API /v1/scan/{symbol} endpoint first."
                )
        elif command == "/approve":
            if len(parts) < 3:
                return "Usage: /approve RECOMMENDATION_ID TOKEN"
            approval = await self.approve_recommendation(parts[1], parts[2])
            response = f"Approved {approval.recommendation_id}."
        elif command == "/reject":
            if len(parts) < 3:
                return "Usage: /reject RECOMMENDATION_ID TOKEN"
            approval = await self.reject_recommendation(parts[1], parts[2])
            response = f"Rejected {approval.recommendation_id}."
        elif command == "/why":
            if len(parts) < 2:
                return "Usage: /why SYMBOL_OR_RECOMMENDATION_ID"
            recommendation = self.get_recommendation(parts[1])
            if not recommendation:
                return "Recommendation not found."
            response = recommendation.explain().why_this_trade
        elif command == "/risk":
            if len(parts) < 2:
                return "Usage: /risk SYMBOL_OR_RECOMMENDATION_ID"
            recommendation = self.get_recommendation(parts[1])
            if not recommendation:
                return "Recommendation not found."
            risk = self.get_risk(recommendation.recommendation_id)
            if not risk:
                return "Risk evaluation not found."
            reasons = [reason for check in risk.checks for reason in check.reasons]
            response = "\n".join([f"{risk.decision}: {risk.summary}", *reasons])
        elif command in {"/positions", "/portfolio"}:
            positions = await self.get_positions(BrokerName.PAPER)
            response = self._format_positions(positions)
        else:
            response = (
                "Supported commands: /scan SYMBOL, /analyze SYMBOL, /approve ID TOKEN, "
                "/reject ID TOKEN, /why SYMBOL, /risk SYMBOL, /positions, /portfolio, "
                "/invest AMOUNT [SYMBOL ...] [PAPER|ZERODHA]"
            )
        if self.notifier and chat_id:
            await self.notifier.send_message(response, chat_id=chat_id)
        return response

    def render_dashboard(self) -> str:
        cards: list[str] = []
        recommendations: Sequence[Recommendation] = sorted(
            self.recommendations.values(),
            key=lambda recommendation: recommendation.run_id or "",
            reverse=True,
        )
        for recommendation in recommendations:
            approval = self.get_approval(recommendation.recommendation_id)
            risk = self.get_risk(recommendation.recommendation_id)
            execution = self.executions.get(recommendation.recommendation_id)
            approval_status = approval.status.value if approval else ApprovalStatus.PENDING.value
            risk_status = risk.decision.value if risk else "N/A"
            execution_status = execution.status if execution else "N/A"
            cards.append(
                "<article style='border:1px solid #ddd;padding:16px;"
                "border-radius:12px;margin-bottom:12px;'>"
                f"<h3>{escape(recommendation.symbol)} · {escape(recommendation.action.value)}</h3>"
                f"<p><strong>Confidence:</strong> {recommendation.confidence:.0%}</p>"
                f"<p><strong>Why:</strong> {escape(recommendation.explain().why_this_trade)}</p>"
                f"<p><strong>Risk:</strong> {escape(risk_status)}</p>"
                f"<p><strong>Approval:</strong> {escape(approval_status)}</p>"
                f"<p><strong>Execution:</strong> {escape(execution_status)}</p>"
                f"<p><code>{escape(recommendation.recommendation_id)}</code></p>"
                "</article>"
            )
        body = "".join(cards) or "<p>No recommendations yet. Call /v1/scan/{symbol} first.</p>"
        return (
            "<html><body style='font-family:system-ui;max-width:960px;"
            "margin:40px auto;padding:0 16px;'>"
            "<h1>AI Trading Framework</h1>"
            "<p>Approval-first operator runtime. "
            "Use the API or Telegram webhook for live interactions.</p>"
            f"{body}"
            "</body></html>"
        )

    def _bootstrap_from_store(self) -> None:
        for run in self.run_store.list_runs():
            self.runs[run.run_id] = run
            for event in run.events:
                if event.event_type == EventType.RECOMMENDATION_CREATED:
                    recommendation = Recommendation.model_validate(event.payload)
                    self.recommendations[recommendation.recommendation_id] = recommendation
                elif event.event_type == EventType.RISK_EVALUATED:
                    latest = next(
                        (
                            recommendation
                            for recommendation in self.recommendations.values()
                            if recommendation.run_id == run.run_id
                        ),
                        None,
                    )
                    if latest:
                        self.risks[latest.recommendation_id] = RiskEvaluation.model_validate(
                            event.payload
                        )
                elif event.event_type in {
                    EventType.APPROVAL_REQUESTED,
                    EventType.APPROVAL_GRANTED,
                    EventType.APPROVAL_REJECTED,
                }:
                    self.approval_service.restore(ApprovalRequest.model_validate(event.payload))
                elif event.event_type in {
                    EventType.EXECUTION_COMPLETED,
                    EventType.EXECUTION_FAILED,
                }:
                    execution = ExecutionResult.model_validate(event.payload)
                    self.executions[execution.recommendation_id] = execution

    def _store_run(self, run: RunRecord) -> None:
        self.runs[run.run_id] = run
        self.run_store.save(run)

    def _require_recommendation(self, recommendation_id: str) -> Recommendation:
        recommendation = self.get_recommendation(recommendation_id)
        if not recommendation:
            raise KeyError(f"Recommendation {recommendation_id} not found.")
        return recommendation

    def _require_risk(self, recommendation_id: str) -> RiskEvaluation:
        risk = self.get_risk(recommendation_id)
        if not risk:
            raise KeyError(f"Risk evaluation for {recommendation_id} not found.")
        return risk

    def _require_run(self, run_id: str | None) -> RunRecord:
        if not run_id:
            raise KeyError("Run id is missing.")
        run = self.runs.get(run_id) or self.run_store.get(run_id)
        if not run:
            raise KeyError(f"Run {run_id} not found.")
        self.runs[run.run_id] = run
        return run

    def _format_recommendation(self, recommendation: Recommendation) -> str:
        approval = self.get_approval(recommendation.recommendation_id)
        risk = self.get_risk(recommendation.recommendation_id)
        explanation: RecommendationExplanation = recommendation.explain()
        approval_text = approval.status.value if approval else "UNKNOWN"
        risk_text = risk.decision.value if risk else "UNKNOWN"
        return (
            f"{recommendation.symbol} {recommendation.action.value}\n"
            f"Confidence: {recommendation.confidence:.0%}\n"
            f"Risk: {risk_text}\n"
            f"Approval: {approval_text}\n"
            f"Why: {explanation.why_this_trade}"
        )

    def _format_positions(self, positions: list) -> str:
        if not positions:
            return "No open positions."
        return "\n".join(
            [
                f"{position.symbol}: qty={position.quantity} avg={position.average_price} "
                f"mark={position.market_price}"
                for position in positions
            ]
        )
