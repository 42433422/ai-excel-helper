"""
FastAPI 依赖函数：用于敏感路由的身份/令牌校验。

当前实现为轻量"软校验"层：
- 读取 `X-User-ID` 请求头作为用户 ID（与审批模块保持一致）
- 对写操作路由（导出/删除/审批）可选地要求 DB 写令牌
- 不强制身份验证（兼容未登录的桌面模式）；强制检查由各路由按需开启

Phase 计划：等待正式会话/JWT 层就绪后，替换为标准 OAuth2 Bearer 校验。
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from fastapi import Header, HTTPException, Request


def _write_lock_enabled() -> bool:
    v = (os.environ.get("FHD_DISABLE_DB_WRITE_LOCK") or "").strip().lower()
    return v not in {"1", "true", "yes", "on"}


class CurrentUser:
    """简化用户上下文（现阶段以 user_id 为主要标识符）。"""

    def __init__(self, user_id: int | None, raw_header: str | None = None):
        self.user_id = user_id
        self.raw_header = raw_header

    @property
    def is_identified(self) -> bool:
        return self.user_id is not None

    def __repr__(self) -> str:
        return f"CurrentUser(user_id={self.user_id})"


def get_current_user(
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
) -> CurrentUser:
    """
    FastAPI `Depends` 工厂：从 X-User-ID 请求头解析当前用户。

    使用方式：
        @router.delete("/api/shipment/records/{id}")
        def delete_record(user: CurrentUser = Depends(get_current_user)):
            ...
    """
    uid: int | None = None
    if x_user_id and str(x_user_id).strip().lstrip("-").isdigit():
        try:
            uid = int(str(x_user_id).strip())
        except (TypeError, ValueError):
            uid = None
    return CurrentUser(user_id=uid, raw_header=x_user_id)


def require_identified_user(
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
) -> CurrentUser:
    """严格版：若未提供合法 X-User-ID 则返回 401。用于高敏感操作（如删除审批流程）。"""
    from fastapi import HTTPException

    user = get_current_user(x_user_id=x_user_id)
    if not user.is_identified and _write_lock_enabled():
        raise HTTPException(
            status_code=401,
            detail={
                "error": "user_id_required",
                "message": "此操作需要提供 X-User-ID 请求头以记录操作人。",
            },
        )
    return user


def session_id_from_request(request: Request) -> str:
    auth = request.headers.get("Authorization") or ""
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    cookie_name = (os.environ.get("SESSION_COOKIE_NAME") or "session_id").strip()
    return (request.cookies.get(cookie_name) or "").strip()


def resolve_session_user(request: Request) -> Any | None:
    from app.application.facades.session_facade import get_session_service

    sid = session_id_from_request(request)
    if not sid:
        return None
    return get_session_service().validate_session(sid)


def get_logged_in_user(request: Request) -> Any:
    user = resolve_session_user(request)
    if not user:
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "message": {"code": "UNAUTHORIZED", "message": "请先登录"},
            },
        )
    if not getattr(user, "is_active", True):
        raise HTTPException(
            status_code=403,
            detail={
                "success": False,
                "message": {"code": "ACCOUNT_DISABLED", "message": "账户已被禁用"},
            },
        )
    return user


def require_permission(permission_code: str) -> Callable[..., Any]:
    def _dependency(request: Request) -> Any:
        user = get_logged_in_user(request)
        from app.application.facades.session_facade import get_auth_service

        if not get_auth_service().has_permission(user, permission_code):
            raise HTTPException(
                status_code=403,
                detail={
                    "success": False,
                    "message": {"code": "FORBIDDEN", "message": "权限不足"},
                },
            )
        return user

    return _dependency
