import pytest

from ai_trading_framework.core.events import EventBus
from ai_trading_framework.models import Event, EventType


@pytest.mark.asyncio
async def test_event_bus_records_and_dispatches():
    bus = EventBus()
    received: list[str] = []

    async def subscriber(event: Event) -> None:
        received.append(event.event_type.value)

    bus.subscribe(EventType.SIGNAL_GENERATED, subscriber)
    await bus.publish(
        Event(event_type=EventType.SIGNAL_GENERATED, run_id="run-1", payload={"symbol": "INFY"})
    )
    assert received == ["SignalGenerated"]
    assert len(bus.history) == 1
