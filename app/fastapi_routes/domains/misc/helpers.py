"""Migrated from legacy_helpers.py (v10)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.infrastructure.auth.dependencies import (
    get_logged_in_user,
    resolve_session_user,
    session_id_from_request,
)

# 纯工具模块；历史路由已迁出，保留空 router 供 legacy_gaps_batch1 聚合 include。
router = APIRouter(deprecated=True)

# 向后兼容别名（v9 路由应改用 infrastructure.auth.dependencies）
_session_id_from_request = session_id_from_request


def _http_exception_to_json(exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
    if "message" in detail and isinstance(detail["message"], dict):
        body = {"success": False, "message": detail["message"]}
    else:
        body = detail if isinstance(detail, dict) else {"success": False, "message": str(detail)}
    return JSONResponse(body, status_code=exc.status_code)


def _require_login_user(request: Request):
    """Deprecated shim：新代码请使用 ``Depends(get_logged_in_user)``。"""
    user = resolve_session_user(request)
    if user is not None:
        return user, None
    try:
        get_logged_in_user(request)
    except HTTPException as exc:
        return None, _http_exception_to_json(exc)
    return user, None


def _require_permission(request: Request, permission_code: str):
    """Deprecated shim：新代码请使用 ``Depends(require_permission(code))``。"""
    user, err = _require_login_user(request)
    if err:
        return None, err
    from app.application.facades.session_facade import get_auth_service

    auth_service = get_auth_service()
    if not auth_service.has_permission(user, permission_code):
        return None, JSONResponse(
            {"success": False, "message": {"code": "FORBIDDEN", "message": "权限不足"}},
            status_code=403,
        )
    return user, None


def _session_to_dict(session: object) -> dict:
    if isinstance(session, dict):
        return {
            "session_id": session.get("session_id"),
            "user_id": session.get("user_id"),
            "title": session.get("title") or "新会话",
            "summary": session.get("summary") or "",
            "message_count": session.get("message_count", 0),
            "last_message_at": session.get("last_message_at"),
            "created_at": session.get("created_at"),
        }
    if isinstance(session, tuple):
        return {
            "session_id": session[1] if len(session) > 1 else None,
            "user_id": session[2] if len(session) > 2 else None,
            "title": (session[3] if len(session) > 3 else None) or "新会话",
            "summary": (session[4] if len(session) > 4 else None) or "",
            "message_count": session[5] if len(session) > 5 else 0,
            "last_message_at": session[6] if len(session) > 6 else None,
            "created_at": session[7] if len(session) > 7 else None,
        }
    return {
        "session_id": getattr(session, "session_id", None),
        "user_id": getattr(session, "user_id", None),
        "title": getattr(session, "title", None) or "新会话",
        "summary": getattr(session, "summary", "") or "",
        "message_count": getattr(session, "message_count", 0),
        "last_message_at": getattr(session, "last_message_at", None),
        "created_at": getattr(session, "created_at", None),
    }


def _message_to_dict(message: object) -> dict:
    if isinstance(message, dict):
        return {
            "id": message.get("id"),
            "session_id": message.get("session_id"),
            "user_id": message.get("user_id"),
            "role": message.get("role"),
            "content": message.get("content"),
            "intent": message.get("intent") or "",
            "metadata": message.get("metadata") or message.get("conversation_metadata") or "",
            "created_at": message.get("created_at"),
        }
    if isinstance(message, tuple):
        return {
            "id": message[0] if len(message) > 0 else None,
            "session_id": message[1] if len(message) > 1 else None,
            "user_id": message[2] if len(message) > 2 else None,
            "role": message[3] if len(message) > 3 else None,
            "content": message[4] if len(message) > 4 else None,
            "intent": (message[5] if len(message) > 5 else "") or "",
            "metadata": (message[6] if len(message) > 6 else "") or "",
            "created_at": message[7] if len(message) > 7 else None,
        }
    return {
        "id": getattr(message, "id", None),
        "session_id": getattr(message, "session_id", None),
        "user_id": getattr(message, "user_id", None),
        "role": getattr(message, "role", None),
        "content": getattr(message, "content", None),
        "intent": getattr(message, "intent", "") or "",
        "metadata": getattr(message, "conversation_metadata", "") or "",
        "created_at": getattr(message, "created_at", None),
    }


def _dispatch_tool_for_approval(
    *, tool_id: str, action: str, params: dict | None = None
) -> dict[str, Any]:
    from app.routes.tools import execute_registered_workflow_tool

    return execute_registered_workflow_tool(tool_id=tool_id, action=action, params=params)
