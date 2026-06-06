"""收货确认 AI 员工（家具）。"""

from __future__ import annotations

from typing import Any, Dict, Optional


def _ok(summary: str = "", *, items=None, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"ok": True, "summary": summary[:4000], "items": list(items or []), "warnings": [], "error": "", "meta": dict(meta or {})}


def _err(msg: str, *, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"ok": False, "summary": msg[:400], "items": [], "warnings": [], "error": msg[:1000], "meta": dict(meta or {})}


def _action(payload: Dict[str, Any]) -> str:
    return str((payload or {}).get("action") or "status").strip() or "status"


EMPLOYEE_ID = "receipt_confirm"


async def run(payload: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    act = _action(payload)
    if act == "status":
        return _ok(
            "收货确认员工就绪；星标命中收货/对账意图后宿主派发 xcagi:workflow-receipt-feedback-signal。",
            meta={"employee_id": EMPLOYEE_ID, "action": act},
        )
    if act == "feedback_ack":
        detail = str((payload or {}).get("detail") or (payload or {}).get("line") or "")[:300]
        return _ok("已记录客户业务进程占位", items=[{"detail": detail}] if detail else [], meta={"employee_id": EMPLOYEE_ID})
    return _err(f"不支持的 action: {act}", meta={"employee_id": EMPLOYEE_ID, "supported": ["status", "feedback_ack"]})
