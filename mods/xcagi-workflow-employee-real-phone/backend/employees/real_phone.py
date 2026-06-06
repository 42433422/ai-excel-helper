"""Workflow employee stub — phone / placeholder."""

from __future__ import annotations

from typing import Any, Dict, Optional


def _ok(summary: str = "", *, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"ok": True, "summary": summary[:4000], "items": [], "warnings": [], "error": "", "meta": dict(meta or {})}


async def run(payload: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    act = str((payload or {}).get("action") or "status").strip() or "status"
    return _ok(
        "ADB 设备连通 → 来电检测/接听 → 语音转写与回复（与状态轮询同步）。",
        meta={"employee_id": "real_phone", "action": act, "mod_role": "furniture"},
    )
