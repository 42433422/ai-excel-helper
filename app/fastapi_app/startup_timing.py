# -*- coding: utf-8 -*-
"""进程启动分段计时（桌面交付与性能优化基线）。"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

_PROCESS_START_MONO = time.monotonic()
_marks: dict[str, float] = {}


def mark_startup(phase: str) -> None:
    key = str(phase or "").strip()
    if not key:
        return
    now = time.monotonic()
    _marks[key] = now
    elapsed_ms = int((now - _PROCESS_START_MONO) * 1000)
    logger.info("[startup_timing] %s elapsed_ms=%s", key, elapsed_ms)


def startup_timing_snapshot() -> dict[str, Any]:
    """返回各阶段相对进程启动的毫秒数（供 /api/desktop/status）。"""
    out: dict[str, Any] = {
        "process_uptime_ms": int((time.monotonic() - _PROCESS_START_MONO) * 1000)
    }
    for key, at in sorted(_marks.items(), key=lambda x: x[1]):
        out[key] = int((at - _PROCESS_START_MONO) * 1000)
    if "mod_staged" in _marks and "mod_background_done" in _marks:
        out["mod_background_load_ms"] = int(
            (_marks["mod_background_done"] - _marks["mod_staged"]) * 1000
        )
    if "lifespan_begin" in _marks and "lifespan_db_done" in _marks:
        out["startup_db_ms"] = int((_marks["lifespan_db_done"] - _marks["lifespan_begin"]) * 1000)
    return out


__all__ = ["mark_startup", "startup_timing_snapshot"]
