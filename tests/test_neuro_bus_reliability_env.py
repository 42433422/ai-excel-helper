"""NeuroBus 可选可靠性层：由环境变量在构造期启用。"""

from __future__ import annotations

import pytest

import app.neuro_bus.dead_letter_queue as dead_letter_queue_mod
from app.neuro_bus.bus import NeuroBus, _neuro_env_flag
from app.neuro_bus.dead_letter_queue import get_dead_letter_queue
from app.neuro_bus.events.base import EventMetadata, EventPriority, NeuroEvent


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1", True),
        ("true", True),
        ("yes", True),
        ("on", True),
        ("0", False),
        ("", False),
        ("off", False),
    ],
)
def test_neuro_env_flag_parsing(monkeypatch, raw: str, expected: bool) -> None:
    monkeypatch.setenv("XCAGI_NEURO_BUS_UNIT_TEST_FLAG", raw)
    assert _neuro_env_flag("XCAGI_NEURO_BUS_UNIT_TEST_FLAG") is expected


def _shutdown_executor(bus: NeuroBus) -> None:
    try:
        bus._executor.shutdown(wait=False)
    except Exception:
        pass


def test_staging_defaults_enable_dedup_and_circuit(monkeypatch) -> None:
    monkeypatch.setenv("FHD_ENV", "staging")
    monkeypatch.delenv("XCAGI_NEURO_BUS_DEDUP", raising=False)
    monkeypatch.delenv("XCAGI_NEURO_BUS_CIRCUIT", raising=False)
    bus = NeuroBus(enable_metrics=False)
    try:
        assert bus._rel_dedup is not None
        assert bus._rel_circuit is not None
        st = bus.get_reliability_status()
        assert st["dedup"] is True
        assert st["circuit_breaker"] is True
        assert st["fhd_env"] == "staging"
    finally:
        _shutdown_executor(bus)


def test_production_profile_all_reliability_layers(monkeypatch) -> None:
    """与 k8s ConfigMap / deploy-production 约定的全开 profile 一致。"""
    monkeypatch.setenv("FHD_ENV", "production")
    for name in (
        "XCAGI_NEURO_BUS_DEDUP",
        "XCAGI_NEURO_BUS_CIRCUIT",
        "XCAGI_NEURO_BUS_RATE_LIMIT",
        "XCAGI_NEURO_BUS_TRACE",
        "XCAGI_NEURO_BUS_LIFELINE",
        "XCAGI_NEURO_BUS_DLQ_AUTO",
        "XCAGI_NEURO_BUS_SLA_LOG",
    ):
        monkeypatch.setenv(name, "1")
    bus = NeuroBus(enable_metrics=False)
    try:
        st = bus.get_reliability_status()
        assert st["dedup"] is True
        assert st["circuit_breaker"] is True
        assert st["rate_limit"] is True
        assert st["tracer"] is True
        assert st["lifeline"] is True
        assert st["dlq_auto"] is True
        assert st["sla_log"] is True
        assert st.get("trace_sample_rate") == 0.1
    finally:
        _shutdown_executor(bus)


def test_get_reliability_status_includes_sla_log(monkeypatch) -> None:
    monkeypatch.setenv("XCAGI_NEURO_BUS_SLA_LOG", "1")
    bus = NeuroBus(enable_metrics=False)
    try:
        st = bus.get_reliability_status()
        assert "sla_log" in st
        assert st["sla_log"] is True
    finally:
        _shutdown_executor(bus)


def test_explicit_off_overrides_staging(monkeypatch) -> None:
    monkeypatch.setenv("FHD_ENV", "staging")
    monkeypatch.setenv("XCAGI_NEURO_BUS_DEDUP", "0")
    monkeypatch.setenv("XCAGI_NEURO_BUS_CIRCUIT", "0")
    bus = NeuroBus(enable_metrics=False)
    try:
        assert bus._rel_dedup is None
        assert bus._rel_circuit is None
    finally:
        _shutdown_executor(bus)


def test_neuro_bus_enables_dedup_when_env_set(monkeypatch) -> None:
    monkeypatch.setenv("XCAGI_NEURO_BUS_DEDUP", "1")
    bus = NeuroBus(enable_metrics=False)
    try:
        assert bus._rel_dedup is not None
    finally:
        _shutdown_executor(bus)


def test_neuro_bus_enables_circuit_when_env_set(monkeypatch) -> None:
    monkeypatch.setenv("XCAGI_NEURO_BUS_CIRCUIT", "1")
    bus = NeuroBus(enable_metrics=False)
    try:
        assert bus._rel_circuit is not None
    finally:
        _shutdown_executor(bus)


def test_neuro_bus_enables_tracer_when_env_set(monkeypatch) -> None:
    monkeypatch.setenv("XCAGI_NEURO_BUS_TRACE", "1")
    bus = NeuroBus(enable_metrics=False)
    try:
        assert bus._rel_tracer is not None
    finally:
        _shutdown_executor(bus)


def _make_event(event_type: str = "dlq.test.event") -> NeuroEvent:
    meta = EventMetadata(domain="test")
    return NeuroEvent(
        event_type=event_type,
        payload={"k": 1},
        priority=EventPriority.NORMAL,
        metadata=meta,
    )


@pytest.mark.asyncio
async def test_handler_failure_enqueues_dlq_when_dlq_auto_env(monkeypatch) -> None:
    dead_letter_queue_mod._dlq_instance = None
    monkeypatch.setenv("XCAGI_NEURO_BUS_DLQ_AUTO", "1")
    bus = NeuroBus(enable_metrics=False)
    try:
        assert bus._dlq_integration is not None
        evt = _make_event()

        async def _boom(_: NeuroEvent) -> None:
            raise RuntimeError("handler boom")

        from app.neuro_bus.bus import HandlerSubscription

        sub = HandlerSubscription(evt.event_type, _boom, is_async=True)
        ok = await bus._call_handler(sub, evt)
        assert ok is False
        stats = get_dead_letter_queue().get_stats()
        assert stats["current_size"] >= 1
    finally:
        _shutdown_executor(bus)
        dead_letter_queue_mod._dlq_instance = None


@pytest.mark.asyncio
async def test_handler_failure_skips_dlq_when_dlq_auto_off(monkeypatch) -> None:
    dead_letter_queue_mod._dlq_instance = None
    monkeypatch.delenv("XCAGI_NEURO_BUS_DLQ_AUTO", raising=False)
    bus = NeuroBus(enable_metrics=False)
    try:
        assert bus._dlq_integration is None
        before = get_dead_letter_queue().get_stats()["current_size"]
        evt = _make_event("dlq.skip.event")

        async def _boom(_: NeuroEvent) -> None:
            raise RuntimeError("no dlq")

        from app.neuro_bus.bus import HandlerSubscription

        sub = HandlerSubscription(evt.event_type, _boom, is_async=True)
        ok = await bus._call_handler(sub, evt)
        assert ok is False
        after = get_dead_letter_queue().get_stats()["current_size"]
        assert after == before
    finally:
        _shutdown_executor(bus)
        dead_letter_queue_mod._dlq_instance = None
