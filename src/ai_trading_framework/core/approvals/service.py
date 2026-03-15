from __future__ import annotations

from datetime import timedelta

from ai_trading_framework.models import ApprovalRequest, ApprovalStatus, BrokerName, utcnow


class ApprovalService:
    def __init__(self, ttl_minutes: int = 30) -> None:
        self.ttl_minutes = ttl_minutes
        self._requests: dict[str, ApprovalRequest] = {}

    def request(self, recommendation_id: str, run_id: str, broker: BrokerName) -> ApprovalRequest:
        approval = ApprovalRequest(
            recommendation_id=recommendation_id,
            run_id=run_id,
            broker=broker,
            expires_at=utcnow() + timedelta(minutes=self.ttl_minutes),
        )
        self._requests[approval.recommendation_id] = approval
        return approval

    def get(self, recommendation_id: str) -> ApprovalRequest | None:
        approval = self._requests.get(recommendation_id)
        if (
            approval
            and approval.status == ApprovalStatus.PENDING
            and approval.expires_at
            and approval.expires_at < utcnow()
        ):
            approval.status = ApprovalStatus.EXPIRED
        return approval

    def approve(self, recommendation_id: str, token: str) -> ApprovalRequest:
        approval = self._require_pending(recommendation_id, token)
        approval.status = ApprovalStatus.APPROVED
        approval.approved_at = utcnow()
        return approval

    def reject(self, recommendation_id: str, token: str) -> ApprovalRequest:
        approval = self._require_pending(recommendation_id, token)
        approval.status = ApprovalStatus.REJECTED
        approval.rejected_at = utcnow()
        return approval

    def consume(self, recommendation_id: str, token: str) -> ApprovalRequest:
        approval = self._requests[recommendation_id]
        if approval.token != token:
            raise ValueError("Invalid approval token.")
        if approval.status != ApprovalStatus.APPROVED:
            raise ValueError("Approval is not in APPROVED state.")
        if approval.consumed_at:
            raise ValueError("Approval token already consumed.")
        approval.status = ApprovalStatus.CONSUMED
        approval.consumed_at = utcnow()
        return approval

    def _require_pending(self, recommendation_id: str, token: str) -> ApprovalRequest:
        approval = self._requests[recommendation_id]
        if approval.token != token:
            raise ValueError("Invalid approval token.")
        if approval.status != ApprovalStatus.PENDING:
            raise ValueError(f"Approval is not pending: {approval.status}.")
        if approval.expires_at and approval.expires_at < utcnow():
            approval.status = ApprovalStatus.EXPIRED
            raise ValueError("Approval request expired.")
        return approval
