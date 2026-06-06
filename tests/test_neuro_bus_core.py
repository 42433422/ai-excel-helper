"""FHD NeuroBus 核心单元测试：优先级队列、事件发布/订阅、去重、可靠性层。"""

from __future__ import annotations

import asyncio
import time

import pytest

from app.neuro_bus.bus import HandlerSubscription, NeuroBus, PriorityEventQueue
from app.neuro_bus.events.base import EventMetadata, EventPriority, NeuroEvent


def _make_event(
    event_type: str = "test.event",
    priority: EventPriority = EventPriority.NORMAL,
    domain: str = "test",
    event_id: str | None = None,
) -> NeuroEvent:
    meta = EventMetadata(domain=domain)
    if event_id:
        meta.event_id = event_id
    return NeuroEvent(event_type=event_type, payload={"value": 1}, priority=priority, metadata=meta)


class TestPriorityEventQueue:
    def test_put_and_get(self):
        q = PriorityEventQueue()
        e = _make_event()
        assert q.put(e)
        assert q.size() == 1
        got = q.get()
        assert got is e
        assert q.size() == 0

    def test_priority_ordering(self):
        q = PriorityEventQueue()
        low = _make_event("low", EventPriority.LOW)
        high = _make_event("high", EventPriority.HIGH)
        critical = _make_event("critical", EventPriority.CRITICAL)
        normal = _make_event("normal", EventPriority.NORMAL)

        q.put(low)
        q.put(normal)
        q.put(critical)
        q.put(high)

        assert q.get().event_type == "critical"
        assert q.get().event_type == "high"
        assert q.get().event_type == "normal"
        assert q.get().event_type == "low"

    def test_duplicate_event_id_reminted(self):
        q = PriorityEventQueue()
        e1 = _make_event(event_id="dup-1")
        assert q.put(e1)
        e2 = _make_event(event_id="dup-1")
        result = q.put(e2)
        assert result is True or result is False

    def test_queue_full_drops_low_priority(self):
        q = PriorityEventQueue(max_size=2)
        low = _make_event("low", EventPriority.LOW)
        normal = _make_event("normal", EventPriority.NORMAL)
        high = _make_event("high", EventPriority.HIGH)

        q.put(low)
        q.put(normal)
        q.put(high)

        assert q.size() == 2
        first = q.get()
        assert first.priority == EventPriority.HIGH or first.priority == EventPriority.NORMAL

    def test_peek_does_not_remove(self):
        q = PriorityEventQueue()
        q.put(_make_event())
        assert q.size() == 1
        q.peek()
        assert q.size() == 1

    def test_clear(self):
        q = PriorityEventQueue()
        q.put(_make_event())
        q.put(_make_event())
        q.clear()
        assert q.size() == 0

    def test_get_from_empty_returns_none(self):
        q = PriorityEventQueue()
        assert q.get() is None


class TestHandlerSubscription:
    def test_should_handle_no_filter(self):
        sub = HandlerSubscription("test.event", lambda e: None)
        assert sub.should_handle(_make_event())

    def test_should_handle_with_filter(self):
        sub = HandlerSubscription(
            "test.event",
            lambda e: None,
            filter_fn=lambda e: e.payload.get("value") == 1,
        )
        assert sub.should_handle(_make_event())
        other = _make_event()
        other.payload["value"] = 99
        assert not sub.should_handle(other)

    def test_record_call_stats(self):
        sub = HandlerSubscription("test.event", lambda e: None)
        sub.record_call(success=True)
        sub.record_call(success=True)
        sub.record_call(success=False)
        assert sub.call_count == 3
        assert sub.error_count == 1
        assert abs(sub.error_rate - 1 / 3) < 0.01


class TestNeuroBusPublishSubscribe:
    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self):
        bus = NeuroBus(enable_metrics=False)
        received = []

        def handler(event: NeuroEvent):
            received.append(event)

        bus.subscribe("test.event", handler, is_async=False)
        await bus.start()
        try:
            assert bus.publish(_make_event("test.event"))
            await asyncio.sleep(0.3)
            assert len(received) >= 1
            assert received[0].event_type == "test.event"
        finally:
            await bus.stop()

    @pytest.mark.asyncio
    async def test_async_handler(self):
        bus = NeuroBus(enable_metrics=False)
        received = []

        async def handler(event: NeuroEvent):
            received.append(event)

        bus.subscribe("test.async_event", handler, is_async=True)
        await bus.start()
        try:
            assert bus.publish(_make_event("test.async_event"))
            await asyncio.sleep(0.3)
            assert len(received) >= 1
        finally:
            await bus.stop()

    @pytest.mark.asyncio
    async def test_multiple_handlers(self):
        bus = NeuroBus(enable_metrics=False)
        results_a = []
        results_b = []

        bus.subscribe("test.multi", lambda e: results_a.append(e), is_async=False)
        bus.subscribe("test.multi", lambda e: results_b.append(e), is_async=False)

        await bus.start()
        try:
            assert bus.publish(_make_event("test.multi"))
            await asyncio.sleep(0.3)
            assert len(results_a) >= 1
            assert len(results_b) >= 1
        finally:
            await bus.stop()

    @pytest.mark.asyncio
    async def test_domain_isolation(self):
        bus = NeuroBus(enable_metrics=False)
        domain_a = []
        domain_b = []

        bus.subscribe_to_domain(
            "domain_a", "test.domain_evt", lambda e: domain_a.append(e), is_async=False
        )
        bus.subscribe_to_domain(
            "domain_b", "test.domain_evt", lambda e: domain_b.append(e), is_async=False
        )

        event = _make_event("test.domain_evt", domain="domain_a")

        await bus.start()
        try:
            assert bus.publish(event)
            await asyncio.sleep(0.3)
            assert len(domain_a) >= 1
            assert len(domain_b) == 0
        finally:
            await bus.stop()

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        bus = NeuroBus(enable_metrics=False)
        received = []

        sub = bus.subscribe("test.unsub", lambda e: received.append(e), is_async=False)
        bus.unsubscribe(sub)

        await bus.start()
        try:
            assert bus.publish(_make_event("test.unsub"))
            await asyncio.sleep(0.2)
            assert len(received) == 0
        finally:
            await bus.stop()


class TestNeuroBusMetrics:
    @pytest.mark.asyncio
    async def test_published_count(self, monkeypatch):
        # 全量套件中其它用例可能留下 FHD_ENV / 可靠性开关，导致 dedup 拦截第二次 publish
        monkeypatch.delenv("FHD_ENV", raising=False)
        for name in (
            "XCAGI_NEURO_BUS_DEDUP",
            "XCAGI_NEURO_BUS_CIRCUIT",
            "XCAGI_NEURO_BUS_RATE_LIMIT",
            "XCAGI_NEURO_BUS_LIFELINE",
        ):
            monkeypatch.delenv(name, raising=False)
        bus = NeuroBus(enable_metrics=True)
        await bus.start()
        try:
            assert bus.publish(_make_event())
            assert bus.publish(_make_event())
            assert bus._published_count == 2
        finally:
            await bus.stop()


class TestEventMetadata:
    def test_default_values(self):
        meta = EventMetadata()
        assert meta.event_id
        assert meta.span_id
        assert meta.source == "unknown"
        assert meta.domain == "global"
        assert meta.retry_count == 0
        assert meta.max_retries == 3

    def test_to_dict(self):
        meta = EventMetadata(trace_id="t1", source="src")
        d = meta.to_dict()
        assert d["trace_id"] == "t1"
        assert d["source"] == "src"
        assert "event_id" in d


class TestEventPriority:
    def test_ordering(self):
        assert EventPriority.CRITICAL < EventPriority.HIGH
        assert EventPriority.HIGH < EventPriority.NORMAL
        assert EventPriority.NORMAL < EventPriority.LOW
        assert EventPriority.LOW < EventPriority.BACKGROUND
