"""微信消息处理 AI 员工（家具）。"""

from __future__ import annotations

from typing import Any, Dict, Optional


def _ok(summary: str = "", *, items=None, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"ok": True, "summary": summary[:4000], "items": list(items or []), "warnings": [], "error": "", "meta": dict(meta or {})}


def _err(msg: str, *, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"ok": False, "summary": msg[:400], "items": [], "warnings": [], "error": msg[:1000], "meta": dict(meta or {})}


def _action(payload: Dict[str, Any]) -> str:
    return str((payload or {}).get("action") or "status").strip() or "status"


EMPLOYEE_ID = "wechat_msg"


async def run(payload: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    act = _action(payload)
    if act == "status":
        return _ok(
            "微信消息处理员工就绪；星标轮询与 xcagi:wechat-ai-task-enqueue 由宿主驱动。",
            meta={"employee_id": EMPLOYEE_ID, "action": act},
        )
    if act == "enqueue_ack":
        contact = str((payload or {}).get("contact") or (payload or {}).get("wxid") or "")[:120]
        line = str((payload or {}).get("line") or "")[:200]
        return _ok(
            "已记录微信任务入队" + (f" · {contact}" if contact else ""),
            items=[{"contact": contact, "line": line}] if contact or line else [],
            meta={"employee_id": EMPLOYEE_ID, "action": act},
        )
    return _err(f"不支持的 action: {act}", meta={"employee_id": EMPLOYEE_ID, "supported": ["status", "enqueue_ack"]})
