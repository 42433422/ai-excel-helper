"""Migrated from legacy_conversation.py (v10)."""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Body, Query
from fastapi.responses import FileResponse, JSONResponse

from app.fastapi_routes.domains.misc.helpers import (
    _message_to_dict,
    _session_to_dict,
)
from app.utils.json_safe import json_safe

logger = logging.getLogger(__name__)

router = APIRouter(tags=["legacy-conversation"], deprecated=True)


@router.get("/api/conversations/{session_id}")
def conversations_get(session_id: str, limit: int = Query(default=50)):
    try:
        from app.application.facades.conversation_facade import get_conversation_service

        service = get_conversation_service()
        messages = service.get_session_messages(session_id, limit)
        sessions = service.get_sessions(user_id=None, limit=1000)
        session_info = None
        for s in sessions:
            current = _session_to_dict(s)
            if current.get("session_id") == session_id:
                session_info = current
                break
        result = [_message_to_dict(m) for m in messages]
        return json_safe({"success": True, "session": session_info, "messages": result})
    except Exception as e:
        logger.error("conversations get: %s", e)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.delete("/api/conversations/{session_id}")
def conversations_delete(session_id: str):
    try:
        from app.application.facades.conversation_facade import get_conversation_service

        service = get_conversation_service()
        success = service.delete_session(session_id)
        return {"success": success}
    except Exception as e:
        logger.error("conversations delete: %s", e)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.put("/api/conversations/{session_id}/title")
def conversations_title_put(session_id: str, body: dict = Body(default_factory=dict)):
    from app.application.facades.conversation_facade import (
        get_conversation_service as get_conversation_app_service,
    )

    service = get_conversation_app_service()
    data = body or {}
    title = data.get("title", "")
    success = service.update_session_title(session_id, title)
    return {"success": success}


@router.get("/api/ai/analyze/export/{export_id}")
def ai_analyze_export(export_id: str):
    try:
        from app.application.facades.conversation_facade import get_data_analysis_service
        from app.utils.path_utils import get_upload_dir

        service = get_data_analysis_service()
        output_path = os.path.join(get_upload_dir(), f"report_{export_id}.xlsx")
        success = service.export_to_excel({}, output_path)
        if success and os.path.exists(output_path):
            return FileResponse(
                output_path,
                filename=f"分析报告_{export_id[:8]}.xlsx",
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        return JSONResponse({"success": False, "message": "导出失败"}, status_code=500)
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.post("/api/ai/message/save")
def ai_message_save(body: dict = Body(default_factory=dict)):
    from app.application.facades.conversation_facade import (
        get_conversation_service as get_conversation_app_service,
    )

    service = get_conversation_app_service()
    if not body:
        return JSONResponse({"success": False, "message": "请求数据不能为空"}, status_code=400)
    session_id = body.get("session_id")
    user_raw = body.get("user_id", "default")
    role = body.get("role")
    content = body.get("content")
    intent = body.get("intent", "")
    metadata = body.get("metadata", "")
    if not session_id:
        return JSONResponse({"success": False, "message": "会话 ID 不能为空"}, status_code=400)
    if not role:
        return JSONResponse({"success": False, "message": "角色不能为空"}, status_code=400)
    if role in ("ai", "bot"):
        role = "assistant"
    if role not in ("user", "assistant", "system"):
        return JSONResponse({"success": False, "message": f"无效的角色：{role}"}, status_code=400)
    if not content:
        return JSONResponse({"success": False, "message": "消息内容不能为空"}, status_code=400)

    user_id_str = str(user_raw) if user_raw is not None else "default"
    try:
        message_id = service.save_message(session_id, user_id_str, role, content, intent, metadata)
        return {"success": True, "message_id": message_id}
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)
