"""
xcagi-core-workflow-employees — Mod（房子）HTTP 面。

四名工作流员工（家具）共用本蓝图：/api/mod/<mod_id>/employees/<employee_id>/run|status
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter

logger = logging.getLogger(__name__)

MOD_ID = "xcagi-core-workflow-employees"

# employee_id -> backend stem (furniture file name without .py)
EMPLOYEES: List[Tuple[str, str, str]] = [
    ("label_print", "label_print", "标签打印 AI 员工"),
    ("shipment_mgmt", "shipment_mgmt", "出货管理 AI 员工"),
    ("receipt_confirm", "receipt_confirm", "收货确认 AI 员工"),
    ("wechat_msg", "wechat_msg", "微信消息处理 AI 员工"),
]


def _resolve_mod_path(_mod_id: str) -> Optional[str]:
    here = os.path.dirname(os.path.abspath(__file__))
    guess = os.path.dirname(here)
    if os.path.isfile(os.path.join(guess, "manifest.json")):
        return guess
    return None


def _load_employee_module(mod_id: str, stem: str):
    try:
        from app.mod_sdk.mods_bus import import_mod_backend_py  # type: ignore
    except ImportError:
        return None
    mod_path = _resolve_mod_path(mod_id)
    if not mod_path:
        return None
    try:
        return import_mod_backend_py(mod_path, mod_id, f"employees/{stem}")
    except Exception:
        logger.exception("load employee module failed mod=%s stem=%s", mod_id, stem)
        return None


def _unified_err(msg: str, **meta: Any) -> Dict[str, Any]:
    return {
        "success": False,
        "data": {
            "ok": False,
            "summary": msg[:400],
            "items": [],
            "warnings": [],
            "error": msg[:1000],
            "meta": meta,
        },
        "error": msg[:500],
    }


async def _build_ctx(mod_id: str, employee_id: str) -> Dict[str, Any]:
    ctx: Dict[str, Any] = {
        "mod_id": mod_id,
        "employee_id": employee_id,
        "logger": logging.getLogger(f"mod.{mod_id}.emp.{employee_id}"),
        "host_base_url": os.environ.get("XCAGI_HOST_BASE_URL", "http://127.0.0.1:5000"),
        "call_llm": None,
        "http_get": None,
        "http_post": None,
    }
    try:
        from app.mod_sdk.mod_employee_llm import mod_employee_complete  # type: ignore

        async def _call_llm(messages, *, max_tokens=1024, temperature=0.2, response_format=None):
            return await mod_employee_complete(
                messages, max_tokens=max_tokens, temperature=temperature, response_format=response_format
            )

        ctx["call_llm"] = _call_llm
    except Exception as exc:
        logger.warning("mod_employee_complete unavailable: %s", exc)

    try:
        import httpx as _httpx

        async def _http_get(url, *, headers=None, timeout=30):
            try:
                async with _httpx.AsyncClient(timeout=float(timeout)) as client:
                    r = await client.get(url, headers=headers or {})
                    return {"ok": r.status_code < 400, "status": r.status_code, "text": r.text, "error": ""}
            except Exception as e:  # noqa: BLE001
                return {"ok": False, "status": 0, "text": "", "error": str(e)[:500]}

        async def _http_post(url, *, json_body=None, data=None, headers=None, timeout=30):
            try:
                async with _httpx.AsyncClient(timeout=float(timeout)) as client:
                    r = await client.post(url, json=json_body, data=data, headers=headers or {})
                    return {"ok": r.status_code < 400, "status": r.status_code, "text": r.text, "error": ""}
            except Exception as e:  # noqa: BLE001
                return {"ok": False, "status": 0, "text": "", "error": str(e)[:500]}

        ctx["http_get"] = _http_get
        ctx["http_post"] = _http_post
    except ImportError:
        logger.warning("httpx not installed; http_get/http_post disabled")

    return ctx


async def _dispatch_run(mod_id: str, emp_id: str, stem: str, payload: Optional[Dict[str, Any]]):
    module = _load_employee_module(mod_id, stem)
    if module is None or not hasattr(module, "run"):
        return _unified_err(
            "employee module not loaded; expected backend/employees/%s.py with async def run",
            employee_id=emp_id,
            stem=stem,
        )
    ctx = await _build_ctx(mod_id, emp_id)
    try:
        run_fn = getattr(module, "run")
        out = run_fn(payload or {}, ctx)
        if asyncio.iscoroutine(out):
            out = await out
        return {"success": True, "data": out}
    except Exception as exc:  # noqa: BLE001
        logger.exception("employee run failed emp=%s", emp_id)
        return _unified_err(f"employee run failed: {exc!s}"[:300], employee_id=emp_id)


def register_fastapi_routes(app, mod_id: str) -> None:
    router = APIRouter(prefix=f"/api/mod/{mod_id}", tags=[f"mod-{mod_id}"])

    @router.get("/status")
    def mod_status():
        return {
            "success": True,
            "data": {
                "mod_id": mod_id,
                "role": "core_workflow_house",
                "employees": [{"id": e[0], "label": e[2], "stem": e[1]} for e in EMPLOYEES],
            },
        }

    @router.get("/employees")
    async def list_employees():
        return {
            "success": True,
            "data": [{"id": e[0], "label": e[2], "api_base_path": f"employees/{e[0]}"} for e in EMPLOYEES],
        }

    for emp_id, stem, label in EMPLOYEES:

        @router.post(f"/employees/{emp_id}/run")
        async def emp_run(payload: Dict[str, Any] | None = None, _eid: str = emp_id, _stem: str = stem):
            return await _dispatch_run(mod_id, _eid, _stem, payload)

        @router.get(f"/employees/{emp_id}/status")
        async def emp_status(_eid: str = emp_id, _stem: str = stem):
            out = await _dispatch_run(mod_id, _eid, _stem, {"action": "status"})
            return out

    app.include_router(router)
    logger.info("xcagi-core-workflow-employees routes registered mod_id=%s employees=%d", mod_id, len(EMPLOYEES))


def mod_init():
    logger.info("xcagi-core-workflow-employees mod_init (1 Mod, %d employees)", len(EMPLOYEES))
