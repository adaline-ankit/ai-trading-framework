from __future__ import annotations

from typing import Any

from ai_trading_framework.core.runtime.operator import OperatorRuntime


class ReplayCapability:
    def __init__(self, runtime: OperatorRuntime) -> None:
        self.runtime = runtime

    def get(self, run_id: str) -> dict[str, Any] | None:
        return self.runtime.replay(run_id)
