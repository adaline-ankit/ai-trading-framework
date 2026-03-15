from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from ai_trading_framework.models import Event, EventType

Subscriber = Callable[[Event], Any | Awaitable[Any]]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[EventType, list[Subscriber]] = defaultdict(list)
        self._history: list[Event] = []

    def subscribe(self, event_type: EventType, subscriber: Subscriber) -> None:
        self._subscribers[event_type].append(subscriber)

    @property
    def history(self) -> list[Event]:
        return list(self._history)

    async def publish(self, event: Event) -> None:
        self._history.append(event)
        for subscriber in self._subscribers.get(event.event_type, []):
            result = subscriber(event)
            if asyncio.iscoroutine(result):
                await result
