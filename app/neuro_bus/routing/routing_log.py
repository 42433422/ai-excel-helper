"""Append-only routing decision log for offline training."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


def _default_log_path() -> Path:
    root = Path(__file__).resolve().parents[3]
    d = root / "resources" / "routing_policies"
    d.mkdir(parents=True, exist_ok=True)
    return d / "routing_decisions.jsonl"


def append_routing_decision(
    trace_id: str | None,
    features: list[float],
    action: str,
    latency_ms: float,
    outcome: str,
    reward: float | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    row = {
        "ts": time.time(),
        "trace_id": trace_id,
        "features": features,
        "action": action,
        "latency_ms": latency_ms,
        "outcome": outcome,
        "reward": reward,
        "extra": extra or {},
    }
    path = Path(os.environ.get("XCAGI_ROUTING_LOG_PATH", str(_default_log_path())))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
