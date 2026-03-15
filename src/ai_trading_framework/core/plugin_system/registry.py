from __future__ import annotations

from importlib.metadata import entry_points
from typing import Any


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, dict[str, Any]] = {}

    def register(self, kind: str, name: str, plugin: Any) -> None:
        self._plugins.setdefault(kind, {})[name] = plugin

    def get(self, kind: str, name: str) -> Any:
        return self._plugins[kind][name]

    def list(self, kind: str) -> dict[str, Any]:
        return dict(self._plugins.get(kind, {}))

    def discover_entry_points(self, group: str = "ai_trading_framework.plugins") -> None:
        for entry_point in entry_points().select(group=group):
            plugin = entry_point.load()
            kind, _, name = entry_point.name.partition(":")
            self.register(kind or "generic", name or entry_point.name, plugin)
