"""XCAGI Android 原生客户端 API（/api/mobile/v1）。"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.security.mobile_jwt import (
    issue_mobile_tokens,
    refresh_mobile_access_token,
    user_id_from_mobile_bearer,
    verify_mobile_jwt,
)
from app.utils.mobile_api import format_mobile_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mobile/v1", tags=["mobile-api"])


class MobileLoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=1)
    account_kind: str = Field(default="enterprise", max_length=32)


class MobileRefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=10)


def _user_public_dict(user) -> dict[str, Any]:
    from app.utils.user_avatar_storage import public_avatar_url

    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "avatar_url": public_avatar_url(getattr(user, "wx_avatar_url", None)),
    }


async def get_mobile_user(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    """Bearer 移动端 JWT 或会话 Cookie / X-Session-ID。"""
    from app.db.models import User
    from app.db.session import get_db

    uid = user_id_from_mobile_bearer(authorization)
    if uid is not None:
        with get_db() as db:
            user = db.query(User).filter(User.id == uid).first()
            if user and user.is_active:
                return user
        return None

    from app.infrastructure.auth.dependencies import resolve_session_user

    return resolve_session_user(request)


def _parse_web_auth_login_response(web_resp: Any) -> tuple[dict[str, Any], int]:
    """解析 ``POST /api/auth/login`` 的 JSONResponse（与 Web 桌面端同源）。"""
    status = int(getattr(web_resp, "status_code", 200) or 200)
    if isinstance(web_resp, JSONResponse):
        raw = web_resp.body
        if not raw:
            return {"success": False, "message": "登录失败"}, status
        if isinstance(raw, memoryview):
            raw = raw.tobytes()
        if isinstance(raw, bytes):
            return json.loads(raw.decode("utf-8")), status
        return json.loads(str(raw)), status
    if isinstance(web_resp, dict):
        return web_resp, status
    return {"success": False, "message": "登录失败"}, status


def _web_login_error_message(payload: dict[str, Any]) -> str:
    err = payload.get("error")
    if isinstance(err, dict):
        msg = str(err.get("message") or "").strip()
        if msg:
            return msg
    return str(payload.get("message") or "登录失败").strip() or "登录失败"


@router.post("/auth/login")
async def mobile_auth_login(body: MobileLoginRequest):
    """与 Web ``POST /api/auth/login`` 共用认证逻辑（市场校验、JIT、account_kind、市场 token）。"""
    from app.application.session_account_meta import normalize_account_kind
    from app.fastapi_routes.domains.auth.routes import auth_login
    from app.mod_sdk.product_skus import resolve_product_sku

    sku = resolve_product_sku()
    default_kind = "enterprise" if sku == "enterprise" else "personal"
    account_kind = normalize_account_kind(body.account_kind, default=default_kind)

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/auth/login",
        "headers": [],
    }
    request = Request(scope)
    web_resp = await auth_login(
        request,
        {
            "username": body.username.strip(),
            "password": body.password,
            "account_kind": account_kind,
        },
    )
    payload, status = _parse_web_auth_login_response(web_resp)
    if not payload.get("success"):
        message = _web_login_error_message(payload)
        code = status if status >= 400 else 401
        return JSONResponse(
            format_mobile_response(
                data={"error": message, "error_id": payload.get("error_id")},
                message=message,
                success=False,
                code=code,
            ),
            status_code=code,
        )

    session_id = str(payload.get("session_id") or "").strip()
    user_raw = payload.get("user")
    if not session_id or not isinstance(user_raw, dict) or user_raw.get("id") is None:
        return JSONResponse(
            format_mobile_response(
                data=None,
                message="会话创建失败",
                success=False,
                code=500,
            ),
            status_code=500,
        )

    resolved_kind = str(payload.get("account_kind") or account_kind).strip() or account_kind
    tokens = issue_mobile_tokens(
        user_id=int(user_raw["id"]),
        session_id=session_id,
        account_kind=resolved_kind,
        username=str(user_raw.get("username") or body.username.strip()),
    )
    data: dict[str, Any] = {
        "user": user_raw,
        "session_id": session_id,
        "account_kind": resolved_kind,
        **tokens,
        "expires_in": 24 * 3600,
    }
    for key in (
        "market_access_token",
        "market_refresh_token",
        "company_brand",
        "market_is_admin",
        "market_is_enterprise",
    ):
        if key in payload and payload[key] is not None:
            data[key] = payload[key]
    return format_mobile_response(data=data, message="登录成功")


@router.post("/auth/refresh")
async def mobile_auth_refresh(body: MobileRefreshRequest):
    tokens = refresh_mobile_access_token(body.refresh_token.strip())
    if not tokens:
        return JSONResponse(
            format_mobile_response(
                data=None,
                message="refresh_token 无效或已过期",
                success=False,
                code=401,
            ),
            status_code=401,
        )
    return format_mobile_response(data={**tokens, "expires_in": 24 * 3600})


@router.get("/host/discover-hint")
async def mobile_host_discover_hint(request: Request):
    from app.fastapi_routes.lan_routes import host_info

    info = await host_info(request)
    instance_name = os.environ.get("SERVICE_BRIDGE_INSTANCE_NAME", "XCAGI 宿主")
    return format_mobile_response(
        data={
            "lan": info.model_dump(),
            "instance_name": instance_name,
            "api_port": int(os.environ.get("PORT", "5000") or 5000),
            "company": "成都修茈科技有限公司",
            "brand_url": "https://xiu-ci.com",
        },
    )


@router.get("/me")
async def mobile_me(request: Request, user=Depends(get_mobile_user)):
    if user is None:
        return JSONResponse(
            format_mobile_response(
                data=None,
                message="未授权",
                success=False,
                code=401,
            ),
            status_code=401,
        )

    from app.application.auth_app_service import get_auth_app_service
    from app.application.session_account_meta import load_session_account_meta

    auth_app = get_auth_app_service()
    permissions = auth_app.get_user_permissions(user)
    sid = ""
    auth_hdr = request.headers.get("Authorization") or ""
    if auth_hdr.startswith("Bearer "):
        payload = verify_mobile_jwt(auth_hdr[7:].strip())
        if payload:
            sid = str(payload.get("session_id") or "")
    if not sid:
        from app.infrastructure.auth.dependencies import session_id_from_request

        sid = session_id_from_request(request)
    meta = load_session_account_meta(sid) if sid else {}

    mods_summary: list[dict[str, str]] = []
    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager

        mgr = get_mod_manager()
        for entry in (mgr.list_mods() or [])[:50]:
            mid = str(entry.get("id") or entry.get("mod_id") or "")
            if mid:
                mods_summary.append({"id": mid})
    except Exception as exc:
        logger.debug("mods list for mobile me: %s", exc)

    return format_mobile_response(
        data={
            "user": _user_public_dict(user),
            "permissions": permissions,
            "account_kind": meta.get("account_kind") or "enterprise",
            "company_brand": meta.get("company_brand") or "成都修茈科技有限公司",
            "mods": mods_summary,
        },
    )


@router.get("/health")
async def mobile_health():
    return format_mobile_response(
        data={"service": "xcagi-mobile", "status": "ok"},
    )


from app.fastapi_routes.mobile_api_extensions import extension_router  # noqa: E402

router.include_router(extension_router)
