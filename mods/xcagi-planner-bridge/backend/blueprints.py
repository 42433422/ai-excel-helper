"""Planner Mod（房子）— 对话 API 门面；执行仍走宿主 Planner（经 app.mod_sdk.planner_compat）。"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Body, Request
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

HOST_PREFIXES = ["/api/ai/chat", "/api/ai/intent"]


def register_fastapi_routes(app, mod_id: str) -> None:
    router = APIRouter(prefix=f"/api/mod/{mod_id}", tags=[f"planner-mod-{mod_id}"])

    @router.get("/status")
    def status():
        return {
            "success": True,
            "data": {
                "mod_id": mod_id,
                "role": "planner_facade",
                "phase": "3d",
                "host_api_prefixes": HOST_PREFIXES,
                "facade_paths": {
                    "chat": f"/api/mod/{mod_id}/chat",
                    "stream": f"/api/mod/{mod_id}/chat/stream",
                    "batch": f"/api/mod/{mod_id}/chat/batch",
                    "unified_chat": f"/api/mod/{mod_id}/unified_chat",
                    "intent_test": f"/api/mod/{mod_id}/intent/test",
                    "tools_registry": f"/api/mod/{mod_id}/tools/registry",
                    "tools_execute": f"/api/mod/{mod_id}/tools/execute",
                },
                "phase_tools": "B",
                "note": "与 /api/ai/chat 契约相同；里程碑 B 工具执行经 /tools/execute 门面。",
            },
        }

    @router.post("/chat")
    async def mod_chat(request: Request, body: dict | None = Body(default=None)):
        from app.mod_sdk.planner_compat import chat

        return await chat(request, body)

    @router.post("/chat/stream")
    async def mod_chat_stream(request: Request, body: dict | None = Body(default=None)):
        from app.mod_sdk.planner_compat import chat_stream, resolve_ai_tier_for_request

        tier = resolve_ai_tier_for_request(request)
        return StreamingResponse(
            chat_stream(request, body),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "X-Planner-Facade-Mod": mod_id,
                "X-AI-Tier": tier,
            },
        )

    @router.post("/chat/batch")
    async def mod_chat_batch(request: Request, body: dict | None = Body(default=None)):
        from app.mod_sdk.planner_compat import chat_batch

        return await chat_batch(request, body)

    @router.post("/unified_chat")
    async def mod_unified_chat(request: Request, body: dict | None = Body(default=None)):
        from app.mod_sdk.planner_compat import chat

        return await chat(request, body)

    @router.post("/unified_chat/batch")
    async def mod_unified_chat_batch(request: Request, body: dict | None = Body(default=None)):
        from app.mod_sdk.planner_compat import chat_batch

        return await chat_batch(request, body)

    @router.post("/intent/test")
    def mod_intent_test(body: dict | None = Body(default=None)):
        from app.mod_sdk.planner_compat import intent_test

        return intent_test(body)

    @router.get("/tools/registry")
    def mod_tools_registry():
        from app.mod_sdk.planner_compat import list_planner_tools_registry

        data = list_planner_tools_registry()
        return {"success": True, "data": data}

    @router.post("/tools/execute")
    def mod_tools_execute(body: dict | None = Body(default=None)):
        from fastapi.responses import JSONResponse

        from app.mod_sdk.planner_compat import execute_planner_tool

        data = execute_planner_tool(body)
        code = 400 if not data.get("ok") else 200
        return JSONResponse({"success": data.get("ok", False), "data": data}, status_code=code)

    @router.get("/host-capabilities")
    async def host_capabilities():
        try:
            import httpx

            base = os.environ.get("XCAGI_HOST_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(f"{base}/api/platform-shell/capabilities")
                if r.status_code < 400:
                    return r.json()
        except Exception as exc:
            logger.warning("host-capabilities proxy failed: %s", exc)
        return {"success": False, "error": "platform-shell unavailable"}

    app.include_router(router)
    logger.info("xcagi-planner-bridge planner facade registered: %s", mod_id)


def mod_init():
    logger.info("xcagi-planner-bridge mod_init (planner facade)")
