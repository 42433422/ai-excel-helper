import asyncio
import time

import pytest

from app.neuro_bus.bus import NeuroBus
from app.neuro_bus.events.base import NeuroEvent


@pytest.mark.asyncio
async def test_neurobus_wakeup_latency():
    bus = NeuroBus()
    await bus.start()

    processed = asyncio.Event()

    async def handler(evt: NeuroEvent):
        processed.set()

    # subscribe to a test event
    bus.subscribe("test.event", handler, is_async=True)

    evt = NeuroEvent(event_type="test.event", payload={})

    t0 = time.perf_counter()
    assert bus.publish(evt)

    # wait for handler to run
    try:
        await asyncio.wait_for(processed.wait(), timeout=0.5)
    finally:
        await bus.stop()

    elapsed_ms = (time.perf_counter() - t0) * 1000
    # Expect wakeup + dispatch to complete within 100ms in normal CI environments
    assert elapsed_ms < 100, f"NeuroBus wakeup/dispatch too slow: {elapsed_ms:.1f}ms"
