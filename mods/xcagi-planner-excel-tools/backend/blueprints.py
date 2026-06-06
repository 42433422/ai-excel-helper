"""Planner Excel 原生工具 Mod — 状态与直接执行端点。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Body

logger = logging.getLogger(__name__)


def register_fastapi_routes(app, mod_id: str) -> None:
    router = APIRouter(prefix=f"/api/mod/{mod_id}", tags=[f"planner-excel-tools-{mod_id}"])

    @router.get("/status")
    def status():
        from app.mod_sdk.planner_native_tools import list_native_planner_tools_summary

        return {
            "success": True,
            "data": {
                "mod_id": mod_id,
                "phase": "F",
                "role": "planner_native_tools",
                **list_native_planner_tools_summary(),
            },
        }

    @router.post("/tools/run")
    def tools_run(body: dict | None = Body(default=None)):
        from app.mod_sdk.planner_native_tools import try_execute_native_planner_tool

        payload = body or {}
        name = str(payload.get("tool_name") or payload.get("name") or "").strip()
        raw, handler_mod = try_execute_native_planner_tool(
            name,
            payload.get("arguments") or payload.get("args") or {},
            workspace_root=payload.get("workspace_root"),
            db_write_token=payload.get("db_write_token"),
        )
        if raw is None:
            return {"success": False, "error": f"tool not handled by native mods: {name}"}
        return {
            "success": True,
            "data": {
                "tool_name": name,
                "result": raw,
                "execution_path": "mod_native",
                "mod_id": handler_mod or mod_id,
            },
        }

    app.include_router(router)
    logger.info("xcagi-planner-excel-tools registered: %s", mod_id)


def mod_init():
    logger.info("xcagi-planner-excel-tools mod_init")
