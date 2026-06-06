"""标签打印 AI 员工（家具）— 薄封装，主链路在宿主副窗事件。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _ok(summary: str = "", *, items=None, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "ok": True,
        "summary": summary[:4000],
        "items": list(items or []),
        "warnings": [],
        "error": "",
        "meta": dict(meta or {}),
    }


def _err(msg: str, *, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"ok": False, "summary": msg[:400], "items": [], "warnings": [], "error": msg[:1000], "meta": dict(meta or {})}


def _action(payload: Dict[str, Any]) -> str:
    return str((payload or {}).get("action") or "status").strip() or "status"


EMPLOYEE_ID = "label_print"


async def run(payload: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    act = _action(payload)
    if act == "status":
        return _ok(
            "标签打印员工就绪；星标命中标签/打印意图后宿主派发 xcagi:workflow-label-print-signal。",
            meta={"employee_id": EMPLOYEE_ID, "action": act, "mod_role": "furniture"},
        )
    if act == "signal_ack":
        line = str((payload or {}).get("line") or "")[:200]
        return _ok(
            "已记录标签/打印信号" + (f"：{line[:80]}" if line else ""),
            items=[{"line": line}] if line else [],
            meta={"employee_id": EMPLOYEE_ID, "action": act},
        )
    return _err(f"不支持的 action: {act}", meta={"employee_id": EMPLOYEE_ID, "supported": ["status", "signal_ack"]})
