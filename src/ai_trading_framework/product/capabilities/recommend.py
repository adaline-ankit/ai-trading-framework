from __future__ import annotations

from typing import Any

from ai_trading_framework.core.orchestration.pipeline import AnalysisPipeline
from ai_trading_framework.core.runtime.operator import OperatorRuntime
from ai_trading_framework.models import Action, BrokerName
from ai_trading_framework.product.state import WatchlistState


class RecommendationCapability:
    def __init__(
        self,
        runtime: OperatorRuntime,
        pipeline: AnalysisPipeline,
        watchlist_state: WatchlistState,
    ) -> None:
        self.runtime = runtime
        self.pipeline = pipeline
        self.watchlist_state = watchlist_state

    async def recommend(
        self,
        *,
        broker: BrokerName,
        symbols: list[str] | None = None,
        notify: bool = True,
    ) -> dict[str, Any]:
        candidates: list[dict[str, Any]] = []
        for symbol in symbols or self.watchlist_state.get_all():
            context, recommendations = await self.pipeline.analyze(symbol, broker=broker)
            run, recommendations, risks = await self.runtime.analyze(
                context,
                recommendations,
                broker=broker,
                notify=notify,
            )
            for recommendation, risk in zip(recommendations, risks, strict=False):
                approval = self.runtime.get_approval(recommendation.recommendation_id)
                score = recommendation.confidence
                if recommendation.action == Action.BUY:
                    score += 0.2
                elif recommendation.action == Action.HOLD:
                    score -= 0.2
                if risk.decision.value != "APPROVED":
                    score -= 0.1
                candidates.append(
                    {
                        "run_id": run.run_id,
                        "recommendation": recommendation.model_dump(mode="json"),
                        "risk": risk.model_dump(mode="json"),
                        "approval": approval.model_dump(mode="json") if approval else None,
                        "score": round(score, 4),
                    }
                )
        candidates.sort(key=lambda item: float(item["score"]), reverse=True)
        return {
            "count": len(candidates),
            "top": candidates[0] if candidates else None,
            "items": candidates,
        }
