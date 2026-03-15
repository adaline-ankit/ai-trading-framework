from __future__ import annotations

from collections import Counter


class MetricsRegistry:
    def __init__(self) -> None:
        self._counters: Counter[str] = Counter()

    def increment(self, metric: str, value: int = 1) -> None:
        self._counters[metric] += value

    def snapshot(self) -> dict[str, int]:
        return dict(self._counters)
