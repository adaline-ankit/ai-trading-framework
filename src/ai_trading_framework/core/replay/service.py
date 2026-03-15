from __future__ import annotations

from ai_trading_framework.models import Event, RunRecord


class ReplayEngine:
    def replay(self, run: RunRecord) -> dict[str, object]:
        latest: dict[str, object] = {
            "run_id": run.run_id,
            "events": [event.model_dump(mode="json") for event in run.events],
        }
        for event in run.events:
            latest[event.event_type.value] = event.payload
        return latest

    def rebuild(self, events: list[Event], run_id: str) -> RunRecord:
        return RunRecord(
            run_id=run_id,
            symbol=events[0].payload.get("symbol", "UNKNOWN") if events else "UNKNOWN",
            events=events,
        )
