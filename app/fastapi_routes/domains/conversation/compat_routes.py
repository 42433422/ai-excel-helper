"""
XCAGI 前端兼容 API — AI 聊天路由（统一对话 / 流式 / 批量）。
宿主保留 /api/ai/*；3d 门面见 /api/mod/xcagi-planner-bridge/chat*。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.application.planner_compat_service import (
    compat_chat_stream_async,
    execute_compat_chat,
    execute_compat_chat_batch,
)
from app.domain.ai.tier import assert_p2_elevated_claim_or_raise, resolve_ai_tier
from app.fastapi_routes.domains.conversation.helpers import (
    XcagiCompatChatBatchBody,
    XcagiCompatChatBody,
)

router = APIRouter(tags=["xcagi-compat"])
logger = logging.getLogger(__name__)


@router.post("/ai/unified_chat/stream")
@router.post("/ai/chat/stream")
async def ai_unified_chat_stream(request: Request, body: XcagiCompatChatBody):
    assert_p2_elevated_claim_or_raise(request)
    tier = resolve_ai_tier(request)
    return StreamingResponse(
        compat_chat_stream_async(request, body, ai_tier=tier),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/ai/chat")
@router.post("/ai/chat/v2")
@router.post("/ai/unified_chat")
async def ai_chat_unified_compat(request: Request, body: XcagiCompatChatBody) -> dict:
    return await execute_compat_chat(request, body)


@router.post("/ai/chat/batch")
@router.post("/ai/chat/v2/batch")
@router.post("/ai/unified_chat/batch")
async def ai_chat_batch_compat(request: Request, body: XcagiCompatChatBatchBody) -> dict:
    return await execute_compat_chat_batch(request, body)


@router.get("/ai/context")
def ai_context_get(user_id: str = Query(default="default")) -> dict:
    _ = user_id
    return {"success": True, "data": {}}


@router.post("/ai/context/clear")
def ai_context_clear(body: dict = Body(default_factory=dict)) -> dict:
    _ = body
    return {"success": True}


@router.get("/ai/config")
def ai_config_get() -> dict:
    return {"success": True, "data": {}}


@router.post("/tts/synthesize")
def tts_synthesize_stub(body: dict = Body(default_factory=dict)) -> dict:
    _ = body.get("text") or body.get("message")
    return {"success": False, "message": "TTS 未在 FHD 兼容层启用", "data": {}}
