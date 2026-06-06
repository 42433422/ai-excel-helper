# -*- coding: utf-8 -*-
"""Single workflow employee Mod HTTP surface."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter

logger = logging.getLogger(__name__)

MOD_ID = "xcagi-workflow-employee-label-print"
EMPLOYEE_ID = "label_print"
EMPLOYEE_STEM = "label_print"
EMPLOYEE_LABEL = "标签打印 AI 员工"


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
    return ctx


async def _dispatch_run(mod_id: str, emp_id: str, stem: str, payload: Optional[Dict[str, Any]]):
    module = _load_employee_module(mod_id, stem)
    if module is None or not hasattr(module, "run"):
        return _unified_err(
            "employee module not loaded",
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
                "role": "workflow_employee_single",
                "employee_id": EMPLOYEE_ID,
                "label": EMPLOYEE_LABEL,
            },
        }

    @router.get("/employees")
    async def list_employees():
        return {
            "success": True,
            "data": [{"id": EMPLOYEE_ID, "label": EMPLOYEE_LABEL, "api_base_path": f"employees/{EMPLOYEE_ID}"}],
        }

    @router.post(f"/employees/{EMPLOYEE_ID}/run")
    async def emp_run(payload: Dict[str, Any] | None = None):
        return await _dispatch_run(mod_id, EMPLOYEE_ID, EMPLOYEE_STEM, payload)

    @router.get(f"/employees/{EMPLOYEE_ID}/status")
    async def emp_status():
        return await _dispatch_run(mod_id, EMPLOYEE_ID, EMPLOYEE_STEM, {"action": "status"})

    app.include_router(router)
    logger.info("workflow employee mod registered mod_id=%s employee=%s", mod_id, EMPLOYEE_ID)


def mod_init():
    logger.info("%s mod_init employee=%s", MOD_ID, EMPLOYEE_ID)
