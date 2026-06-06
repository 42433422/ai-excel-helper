"""出货管理 AI 员工（家具）。"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _ok(summary: str = "", *, items=None, warnings=None, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "ok": True,
        "summary": summary[:4000],
        "items": list(items or []),
        "warnings": list(warnings or []),
        "error": "",
        "meta": dict(meta or {}),
    }


def _err(msg: str, *, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"ok": False, "summary": msg[:400], "items": [], "warnings": [], "error": msg[:1000], "meta": dict(meta or {})}


def _action(payload: Dict[str, Any]) -> str:
    return str((payload or {}).get("action") or "status").strip() or "status"


async def _host_get(ctx: Dict[str, Any], path: str) -> Dict[str, Any]:
    http_get = ctx.get("http_get")
    if not callable(http_get):
        return {"ok": False, "error": "http_get unavailable"}
    base = str(ctx.get("host_base_url") or "http://127.0.0.1:5000").rstrip("/")
    url = f"{base}{path if path.startswith('/') else '/' + path}"
    try:
        out = await http_get(url, timeout=30)
        return out if isinstance(out, dict) else {"ok": False, "error": "invalid response"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:500]}


EMPLOYEE_ID = "shipment_mgmt"


async def run(payload: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    act = _action(payload)
    if act == "status":
        return _ok("出货管理员工就绪；对话开单与打印后审计由宿主工作流驱动。", meta={"employee_id": EMPLOYEE_ID, "action": act})
    if act == "audit_summary":
        unit = str((payload or {}).get("purchaseUnit") or "").strip()
        headline = str((payload or {}).get("headline") or "").strip()
        resp = await _host_get(ctx, "/api/shipment/list?limit=5")
        if not resp.get("ok"):
            return _ok(
                (headline or "审计占位：宿主出货列表暂不可用（仍可由前端工作流完成审计展示）。"),
                warnings=[str(resp.get("error") or "unavailable")[:200]],
                meta={"employee_id": EMPLOYEE_ID, "action": act, "purchase_unit": unit[:120]},
            )
        text = str(resp.get("text") or "")[:500]
        summary = headline or "已请求宿主出货记录摘要（薄封装）。"
        return _ok(
            summary,
            items=[{"snippet": text, "purchase_unit": unit}] if text or unit else [],
            meta={"employee_id": EMPLOYEE_ID, "action": act},
        )
    return _err(f"不支持的 action: {act}", meta={"employee_id": EMPLOYEE_ID, "supported": ["status", "audit_summary"]})
