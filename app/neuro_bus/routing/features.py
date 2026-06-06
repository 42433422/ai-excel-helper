"""Fixed-size feature vector for routing policy (deterministic, no external deps)."""

from __future__ import annotations

import math
from typing import Any

from app.neuro_bus.events.base import EventPriority, NeuroEvent


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def build_routing_features(
    text: str,
    event: NeuroEvent | None = None,
    extra: dict[str, Any] | None = None,
) -> list[float]:
    """
    Returns length-16 vector: normalized counts, priority, optional confidence from ``extra``.
    """
    extra = extra or {}
    t = text or ""
    n = max(len(t), 1)
    ep = EventPriority.NORMAL.value
    if event is not None:
        ep = float(event.priority.value)

    conf = float(extra.get("intent_confidence", 0.0) or 0.0)
    depth = float(extra.get("session_depth", 0.0) or 0.0)

    features = [
        min(len(t) / 512.0, 1.0),
        min(t.count("\n") / 20.0, 1.0),
        min(t.count("?") / 5.0, 1.0),
        1.0 if any(k in t for k in ("打印", "出货", "订单", "库存")) else 0.0,
        1.0 if any(k in t.lower() for k in ("print", "ship", "order")) else 0.0,
        ep / 4.0,
        _clamp01(conf),
        _clamp01(depth / 50.0),
        min(float(sum(1 for c in t if c.isdigit())) / 10.0, 1.0),
        1.0 if t.strip().startswith("/") else 0.0,
        math.sin(min(n, 200) / 200.0 * math.pi),
        math.cos(min(n, 200) / 200.0 * math.pi),
        min(len(t.encode("utf-8")) / 1024.0, 1.0),
        float(bool(extra.get("user_override"))),
        float(bool(extra.get("system_overload"))),
        float(bool(event is not None)),
    ]
    return features
