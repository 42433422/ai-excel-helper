"""Glue: MLP policy -> ProcessorCoordinator ``RoutingDecision`` + JSONL logging."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from app.domain.neuro.processors.coordinator import ProcessorType, RoutingDecision
from app.neuro_bus.events.base import NeuroEvent
from app.neuro_bus.routing.features import build_routing_features
from app.neuro_bus.routing.policy_nn import predict_action_index
from app.neuro_bus.routing.routing_log import append_routing_decision

logger = logging.getLogger(__name__)

_ACTION_ORDER = (ProcessorType.REFLEX, ProcessorType.SUBCONSCIOUS, ProcessorType.CONSCIOUS)


def decide_processor_with_policy(
    text: str,
    event: NeuroEvent | None = None,
    *,
    trace_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> RoutingDecision | None:
    raw = (os.environ.get("XCAGI_ROUTING_POLICY_ENABLED") or "").strip().lower()
    if raw not in {"1", "true", "yes", "on"}:
        return None
    t0 = time.perf_counter()
    feats = build_routing_features(text, event, extra)
    idx = predict_action_index(feats)
    if idx < 0:
        return None
    if idx >= len(_ACTION_ORDER):
        return None
    proc = _ACTION_ORDER[idx]
    latency_ms = (time.perf_counter() - t0) * 1000
    tid = trace_id
    if tid is None and event is not None:
        tid = event.metadata.trace_id
    append_routing_decision(
        trace_id=tid,
        features=feats,
        action=proc.value,
        latency_ms=latency_ms,
        outcome="policy_selected",
        reward=None,
        extra={"source": "policy_mlp"},
    )
    return RoutingDecision(
        processor_type=proc,
        confidence=0.72,
        reason=f"routing_policy_mlp:{idx}",
    )
