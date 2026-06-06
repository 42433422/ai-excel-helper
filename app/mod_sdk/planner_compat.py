# -*- coding: utf-8 -*-
"""Mod SDK：Planner 对话门面（3d）。Mod ``xcagi-planner-bridge`` 经此调用宿主 Planner。"""

from __future__ import annotations

from typing import Any

from fastapi import Request

from app.application.planner_compat_service import (
    compat_chat_stream_async,
    execute_compat_chat,
    execute_compat_chat_batch,
)
from app.fastapi_routes.xcagi_compat_chat_helpers import (
    XcagiCompatChatBatchBody,
    XcagiCompatChatBody,
)

PLANNER_FACADE_MOD_ID = "xcagi-planner-bridge"


async def chat(request: Request, body: dict[str, Any] | None) -> dict[str, Any]:
    model = XcagiCompatChatBody.model_validate(body or {})
    return await execute_compat_chat(request, model)


async def chat_batch(request: Request, body: dict[str, Any] | None) -> dict[str, Any]:
    model = XcagiCompatChatBatchBody.model_validate(body or {})
    return await execute_compat_chat_batch(request, model)


async def chat_stream(request: Request, body: dict[str, Any] | None):
    from app.domain.ai.tier import assert_p2_elevated_claim_or_raise, resolve_ai_tier

    assert_p2_elevated_claim_or_raise(request)
    tier = resolve_ai_tier(request)
    model = XcagiCompatChatBody.model_validate(body or {})
    async for chunk in compat_chat_stream_async(request, model, ai_tier=tier):
        yield chunk


def resolve_ai_tier_for_request(request: Request) -> str:
    from app.domain.ai.tier import resolve_ai_tier

    return resolve_ai_tier(request)


def intent_test(body: dict[str, Any] | None) -> dict[str, Any]:
    from fastapi.responses import JSONResponse

    from app.routes.ai_chat import recognize_intents

    message = str((body or {}).get("message") or "").strip()
    if not message:
        return JSONResponse({"success": False, "message": "消息内容不能为空"}, status_code=400)
    try:
        return {"success": True, "data": recognize_intents(message)}
    except Exception as e:
        return JSONResponse(
            {"success": False, "message": f"意图识别失败：{str(e)}"},
            status_code=500,
        )


def list_planner_tools_registry() -> dict[str, Any]:
    from app.mod_sdk.planner_tools import list_planner_tools_registry_detail

    return list_planner_tools_registry_detail()


def execute_planner_tool(body: dict[str, Any] | None) -> dict[str, Any]:
    from app.mod_sdk.planner_tools import execute_planner_tool_from_body

    return execute_planner_tool_from_body(body)


__all__ = [
    "PLANNER_FACADE_MOD_ID",
    "chat",
    "chat_batch",
    "chat_stream",
    "execute_compat_chat",
    "execute_compat_chat_batch",
    "compat_chat_stream_async",
    "intent_test",
    "list_planner_tools_registry",
    "execute_planner_tool",
]
