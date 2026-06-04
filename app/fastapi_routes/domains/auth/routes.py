"""Migrated from legacy_auth.py (v10)."""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from app.infrastructure.auth.dependencies import (
    get_logged_in_user,
    require_permission,
    session_id_from_request,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["legacy-auth"], deprecated=True)

_require_admin = require_permission("admin.manage_users")


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


def _session_meta_for_response(request: Request) -> dict[str, Any]:
    from app.application.session_account_meta import load_session_account_meta

    sid = session_id_from_request(request)
    if not sid:
        return {}
    meta = load_session_account_meta(sid)
    return meta if meta else {}


@router.get("/api/auth/me")
def auth_me(request: Request, user=Depends(get_logged_in_user)):
    from app.application.auth_app_service import get_auth_app_service

    auth_app_service = get_auth_app_service()
    permissions = auth_app_service.get_user_permissions(user)
    session_meta = _session_meta_for_response(request)
    return {
        "success": True,
        "data": {
            "user": _user_public_dict(user),
            "permissions": permissions,
            "account_kind": session_meta.get("account_kind") or "enterprise",
            "company_brand": session_meta.get("company_brand") or "",
            "market_is_admin": bool(session_meta.get("market_is_admin")),
            "market_is_enterprise": bool(session_meta.get("market_is_enterprise")),
            "impersonating_market_user_id": session_meta.get("impersonating_market_user_id"),
            "impersonating_username": session_meta.get("impersonating_username") or "",
        },
    }


@router.get("/api/auth/session/validate")
async def auth_session_validate(request: Request):
    from app.application.auth_app_service import get_auth_app_service

    session_id = session_id_from_request(request)
    if not session_id:
        # 使用 200：避免前端 api.get 将「未登录」当成 HTTP 错误刷屏；语义由 success/valid 表达。
        return JSONResponse(
            {
                "success": False,
                "valid": False,
                "error": {"code": "NO_SESSION", "message": "无会话信息"},
            },
            status_code=200,
        )
    auth_app_service = get_auth_app_service()
    session_info = auth_app_service.session_manager.get_session_info(session_id)
    if not session_info:
        return JSONResponse(
            {
                "success": False,
                "valid": False,
                "error": {"code": "INVALID_SESSION", "message": "会话无效或已过期"},
            },
            status_code=200,
        )

    try:
        from app.mod_sdk.product_skus import resolve_product_sku

        if resolve_product_sku() == "enterprise":
            from app.fastapi_routes.market_account import resolve_valid_market_access_token

            market_tok = await resolve_valid_market_access_token(session_id)
            if not market_tok:
                return JSONResponse(
                    {
                        "success": False,
                        "valid": False,
                        "error": {
                            "code": "MARKET_NOT_BOUND",
                            "message": (
                                "企业版需使用修茈市场企业级账号登录。"
                                "若此前仅用本地管理员进入，请退出后重新登录。"
                            ),
                        },
                    },
                    status_code=200,
                )
    except Exception:
        logger.exception("enterprise market session check on validate failed")

    entitled_mod_ids: list[str] = []
    try:
        from app.enterprise.mod_entitlements import (
            get_cached_entitled_client_mod_ids,
            sync_entitlements_for_session,
        )

        entitled = await sync_entitlements_for_session(session_id)
        if entitled:
            entitled_mod_ids = sorted(entitled)
        else:
            cached = get_cached_entitled_client_mod_ids()
            if cached is not None:
                entitled_mod_ids = sorted(cached)
    except Exception:
        logger.exception("sync enterprise entitlements on validate failed")
    session_meta = _session_meta_for_response(request)
    payload: dict[str, Any] = {"success": True, "valid": True, "data": session_info}
    if entitled_mod_ids:
        payload["entitled_mod_ids"] = entitled_mod_ids
    if session_meta:
        payload["account_kind"] = session_meta.get("account_kind")
        payload["company_brand"] = session_meta.get("company_brand")
        payload["market_is_admin"] = session_meta.get("market_is_admin")
        payload["market_is_enterprise"] = session_meta.get("market_is_enterprise")
        payload["impersonating_market_user_id"] = session_meta.get("impersonating_market_user_id")
        payload["impersonating_username"] = session_meta.get("impersonating_username")
    return payload


def _market_user_email_from_raw(raw: Any) -> str:
    if not isinstance(raw, dict):
        return ""
    user = raw.get("user")
    if isinstance(user, dict) and user.get("email"):
        return str(user.get("email") or "").strip()
    data = raw.get("data")
    if isinstance(data, dict):
        inner = data.get("user")
        if isinstance(inner, dict) and inner.get("email"):
            return str(inner.get("email") or "").strip()
    return ""


def _normalize_auth_email(email: str) -> str:
    return (email or "").strip().lower()


def _find_local_users_by_email(email: str) -> list:
    from sqlalchemy import func

    from app.db.models.user import User
    from app.db.session import get_db

    norm = _normalize_auth_email(email)
    if not norm or "@" not in norm:
        return []
    with get_db() as db:
        return (
            db.query(User)
            .filter(func.lower(User.email) == norm)
            .filter(User.is_active.is_(True))
            .order_by(User.id.asc())
            .all()
        )


def _sync_local_password_for_email(email: str, new_password: str) -> int:
    from app.application.auth_app_service import get_auth_app_service

    auth_app_service = get_auth_app_service()
    updated = 0
    for user in _find_local_users_by_email(email):
        result = auth_app_service.reset_password(int(user.id), new_password)
        if result.get("success"):
            updated += 1
    return updated


def _jit_create_local_user_for_enterprise(username: str, password: str, email: str = "") -> bool:
    from app.db.models.user import User
    from app.db.session import get_db
    from app.utils.password_hash import generate_password_hash
    from app.utils.time import utc_now_naive

    with get_db() as db:
        if db.query(User).filter(User.username == username).first():
            return False
        db.add(
            User(
                username=username,
                password=generate_password_hash(password),
                display_name=username,
                email=email or "",
                role="user",
                is_active=True,
                created_at=utc_now_naive(),
            )
        )
        db.commit()
    return True


@router.get("/api/runtime/product-sku")
def runtime_product_sku():
    from app.mod_sdk.product_skus import resolve_product_sku

    sku = resolve_product_sku()
    return {
        "success": True,
        "data": {"sku": sku or "generic", "is_enterprise_edition": sku == "enterprise"},
    }


def _open_registration_allowed(sku: str) -> bool:
    raw = (os.environ.get("FHD_ALLOW_OPEN_REGISTRATION") or "").strip().lower()
    if raw in ("0", "false", "no"):
        return False
    if raw in ("1", "true", "yes"):
        return True
    return sku != "enterprise"


def _attach_session_cookie(response: JSONResponse, session_id: str | None) -> JSONResponse:
    sid = (session_id or "").strip()
    if not sid:
        return response
    cookie_name = os.environ.get("SESSION_COOKIE_NAME", "session_id")
    max_age = int(os.environ.get("SESSION_COOKIE_MAX_AGE", "315360000"))
    response.set_cookie(
        key=cookie_name,
        value=sid,
        max_age=max_age,
        httponly=os.environ.get("SESSION_COOKIE_HTTPONLY", "1") not in ("0", "false", "False"),
        secure=os.environ.get("SESSION_COOKIE_SECURE", "").lower() in ("1", "true", "yes"),
        samesite=os.environ.get("SESSION_COOKIE_SAMESITE", "Lax"),
        path="/",
    )
    return response


@router.post("/api/auth/forgot-account")
def auth_forgot_account(body: dict = Body(default_factory=dict)):
    """Look up local PostgreSQL users by email (same DB as login)."""
    email = _normalize_auth_email(str(body.get("email") or ""))
    if not email or "@" not in email:
        return JSONResponse(
            {
                "success": False,
                "error": {"code": "INVALID_INPUT", "message": "请填写有效邮箱"},
            },
            status_code=400,
        )
    users = _find_local_users_by_email(email)
    usernames = [str(u.username) for u in users if u.username]
    if usernames:
        message = f"找到 {len(usernames)} 个与本机数据库关联的账号"
    else:
        message = "本机数据库中未找到该邮箱对应的账号，可尝试注册或联系管理员"
    return {
        "success": True,
        "message": message,
        "data": {"usernames": usernames, "found": bool(usernames)},
    }


@router.post("/api/auth/forgot-password/send-code")
async def auth_forgot_password_send_code(body: dict = Body(default_factory=dict)):
    """Send reset code via Xiuci market API; uses XCAGI_MARKET_BASE_URL (e.g. production server)."""
    from app.fastapi_routes.market_account import send_market_reset_password_code

    email = _normalize_auth_email(str(body.get("email") or ""))
    if not email or "@" not in email:
        return JSONResponse(
            {
                "success": False,
                "error": {"code": "INVALID_INPUT", "message": "请填写有效邮箱"},
            },
            status_code=400,
        )
    local_users = _find_local_users_by_email(email)
    result = await send_market_reset_password_code(email)
    if not result.get("success"):
        hint = result.get("message", "发送失败")
        if local_users:
            hint = f"{hint}（本机库中有该邮箱用户，请确认修茈市场服务与邮件配置正常）"
        return JSONResponse(
            {"success": False, "error": {"code": "SEND_CODE_FAILED", "message": hint}},
            status_code=502,
        )
    return {
        "success": True,
        "message": result.get("message", "若该邮箱已注册，将收到验证码"),
        "data": {
            "market_base_url": result.get("market_base_url"),
            "local_user_count": len(local_users),
        },
    }


@router.post("/api/auth/forgot-password/reset")
async def auth_forgot_password_reset(body: dict = Body(default_factory=dict)):
    """Reset password on market, then sync matching users in local PostgreSQL."""
    from app.fastapi_routes.market_account import reset_market_password_with_code

    email = _normalize_auth_email(str(body.get("email") or ""))
    code = str(body.get("code") or body.get("verification_code") or "").strip()
    new_password = str(body.get("new_password") or body.get("password") or "")
    if not email or "@" not in email:
        return JSONResponse(
            {
                "success": False,
                "error": {"code": "INVALID_INPUT", "message": "请填写有效邮箱"},
            },
            status_code=400,
        )
    if len(new_password) < 6:
        return JSONResponse(
            {
                "success": False,
                "error": {"code": "WEAK_PASSWORD", "message": "新密码至少 6 个字符"},
            },
            status_code=400,
        )
    market_result = await reset_market_password_with_code(email, code, new_password)
    if not market_result.get("success"):
        return JSONResponse(
            {
                "success": False,
                "error": {
                    "code": "MARKET_RESET_FAILED",
                    "message": market_result.get("message", "重置失败"),
                },
            },
            status_code=400,
        )
    local_updated = _sync_local_password_for_email(email, new_password)
    return {
        "success": True,
        "message": "密码已重置，请使用新密码登录",
        "data": {"local_users_updated": local_updated},
    }


@router.post("/api/auth/register")
async def auth_register(request: Request, body: dict = Body(default_factory=dict)):
    """Register locally (PostgreSQL users) and optionally on Xiuci market; then create session."""
    from app.application import get_user_app_service
    from app.application.auth_app_service import get_auth_app_service
    from app.fastapi_routes.market_account import (
        login_market_with_password,
        register_market_user,
        save_session_market_token,
    )
    from app.mod_sdk.product_skus import resolve_product_sku

    username = (body.get("username") or "").strip()
    password = body.get("password", "")
    email = (body.get("email") or "").strip()
    verification_code = str(body.get("verification_code") or body.get("code") or "").strip()

    if not username or not password:
        return JSONResponse(
            {
                "success": False,
                "error": {"code": "INVALID_INPUT", "message": "用户名和密码不能为空"},
            },
            status_code=400,
        )
    if len(password) < 6:
        return JSONResponse(
            {
                "success": False,
                "error": {"code": "WEAK_PASSWORD", "message": "密码至少 6 个字符"},
            },
            status_code=400,
        )

    sku = resolve_product_sku() or "generic"
    auth_app_service = get_auth_app_service()

    if sku == "enterprise":
        if not email:
            return JSONResponse(
                {
                    "success": False,
                    "error": {"code": "INVALID_INPUT", "message": "企业版注册需填写邮箱"},
                },
                status_code=400,
            )
        market_reg = await register_market_user(username, password, email, verification_code)
        if not market_reg.get("success"):
            return JSONResponse(
                {
                    "success": False,
                    "error": {
                        "code": "MARKET_REGISTER_FAILED",
                        "message": market_reg.get("message", "修茈市场注册失败"),
                    },
                },
                status_code=400,
            )
        email_market = _market_user_email_from_raw(market_reg.get("raw")) or email
        _jit_create_local_user_for_enterprise(username, password, email_market)
        result = auth_app_service.login(username, password)
        if not result.get("success"):
            return JSONResponse(
                {
                    "success": False,
                    "error": {
                        "code": "LOCAL_LOGIN_AFTER_REGISTER",
                        "message": result.get("message", "注册成功但本地登录失败"),
                    },
                },
                status_code=500,
            )
        session_id = result.get("session_id")
        mtok = str(market_reg.get("token") or "").strip()
        mrefresh = str(market_reg.get("refresh_token") or "").strip()
        if session_id and mtok:
            save_session_market_token(str(session_id), mtok, mrefresh or None)
            result["market_access_token"] = mtok
            if mrefresh:
                result["market_refresh_token"] = mrefresh
    else:
        if not _open_registration_allowed(sku):
            return JSONResponse(
                {
                    "success": False,
                    "error": {
                        "code": "REGISTRATION_DISABLED",
                        "message": "本部署未开放自助注册，请联系管理员创建账号",
                    },
                },
                status_code=403,
            )
        user_service = get_user_app_service()
        created = user_service.create_user(
            username=username,
            password=password,
            display_name=(body.get("display_name") or username),
            email=email,
            role="viewer",
        )
        if not created.get("success"):
            msg = created.get("message", "创建用户失败")
            if "已存在" in msg or "unique" in msg.lower():
                msg = "用户名已存在"
            return JSONResponse(
                {"success": False, "error": {"code": "CREATE_FAILED", "message": msg}},
                status_code=400,
            )
        result = auth_app_service.login(username, password)
        if not result.get("success"):
            return JSONResponse(
                {
                    "success": False,
                    "error": {
                        "code": "LOGIN_AFTER_REGISTER",
                        "message": result.get("message", "注册成功但登录失败"),
                    },
                },
                status_code=500,
            )
        session_id = result.get("session_id")
        try:
            market_result = await login_market_with_password(username, password)
            if market_result.get("success"):
                mtok = str(market_result.get("token") or "").strip()
                mrefresh = str(market_result.get("refresh_token") or "").strip()
                if session_id and mtok:
                    save_session_market_token(str(session_id), mtok, mrefresh or None)
                    result["market_access_token"] = mtok
                    if mrefresh:
                        result["market_refresh_token"] = mrefresh
        except Exception:
            logger.exception("optional market sync after local register failed")

    payload = {"success": True, **result}
    return _attach_session_cookie(JSONResponse(payload), result.get("session_id"))


@router.post("/api/auth/login")
async def auth_login(request: Request, body: dict = Body(default_factory=dict)):
    from app.application.auth_app_service import get_auth_app_service
    from app.fastapi_routes.market_account import (
        login_market_with_password,
        save_session_market_token,
    )
    from app.mod_sdk.product_skus import resolve_product_sku

    username = (body.get("username") or "").strip()
    password = body.get("password", "")
    if not username or not password:
        return JSONResponse(
            {
                "success": False,
                "error": {"code": "INVALID_INPUT", "message": "用户名和密码不能为空"},
            },
            status_code=400,
        )
    from app.application.session_account_meta import (
        company_brand_from_user_blob,
        extract_market_user_blob,
        normalize_account_kind,
        persist_session_account_meta,
        validate_account_kind_for_market,
    )

    auth_app_service = get_auth_app_service()
    sku = resolve_product_sku()
    market_result: dict[str, Any] | None = None
    account_kind = normalize_account_kind(
        body.get("account_kind"),
        default="enterprise" if sku == "enterprise" else "personal",
    )

    if sku == "enterprise":
        market_result = await login_market_with_password(username, password)
        if not market_result.get("success"):
            try:
                status_code = int(market_result.get("status_code") or 0)
            except (TypeError, ValueError):
                status_code = 0
            if status_code < 400:
                status_code = 502
            message = str(market_result.get("message") or "修茈市场账号验证失败").strip()
            error_code = "MARKET_AUTH_UNAVAILABLE" if status_code >= 500 else "MARKET_AUTH_FAILED"
            return JSONResponse(
                {
                    "success": False,
                    "message": message,
                    "error": {
                        "code": error_code,
                        "message": message,
                    },
                    "market_account": {
                        "success": False,
                        "market_base_url": market_result.get("market_base_url"),
                        "message": message,
                    },
                },
                status_code=status_code,
            )
        kind_err = validate_account_kind_for_market(
            account_kind,
            is_enterprise=bool(market_result.get("is_enterprise")),
            is_market_admin=bool(market_result.get("is_market_admin")),
        )
        if kind_err:
            return JSONResponse(
                {
                    "success": False,
                    "message": kind_err,
                    "error": {"code": "ACCOUNT_KIND_MISMATCH", "message": kind_err},
                },
                status_code=403,
            )
        result = auth_app_service.login(username, password)
        if not result["success"]:
            from app.db.models.user import User
            from app.db.session import get_db

            try:
                from app.db.init_db import ensure_runtime_auth_bootstrap

                ensure_runtime_auth_bootstrap(swallow_errors=True)
                with get_db() as db:
                    exists = db.query(User).filter(User.username == username).first()
            except Exception as db_exc:
                logger.exception("enterprise login user lookup failed")
                return JSONResponse(
                    {
                        "success": False,
                        "error": {
                            "code": "DATABASE_ERROR",
                            "message": f"本地用户库不可用：{db_exc}",
                        },
                    },
                    status_code=503,
                )
            if exists:
                return JSONResponse(
                    {
                        "success": False,
                        "error": {
                            "code": "LOCAL_AUTH_MISMATCH",
                            "message": (
                                "本地账号密码与修茈市场账号不一致。"
                                "请使用与市场相同的密码，或联系管理员重置本地用户密码。"
                            ),
                        },
                    },
                    status_code=401,
                )
            email = _market_user_email_from_raw(market_result.get("raw"))
            if not _jit_create_local_user_for_enterprise(username, password, email):
                return JSONResponse(
                    {
                        "success": False,
                        "error": {
                            "code": "LOCAL_USER_CREATE_FAILED",
                            "message": "无法为本机创建与企业账号绑定的本地用户",
                        },
                    },
                    status_code=500,
                )
            result = auth_app_service.login(username, password)
            if not result["success"]:
                return JSONResponse(result, status_code=401)
    else:
        result = auth_app_service.login(username, password)
        if not result["success"]:
            return JSONResponse(result, status_code=401)

    session_id = result.get("session_id")
    if session_id:
        try:
            if sku != "enterprise":
                market_result = await login_market_with_password(username, password)
            if market_result is None:
                market_result = await login_market_with_password(username, password)
            mtok = str(market_result.get("token") or "").strip()
            mrefresh = str(market_result.get("refresh_token") or "").strip()
            if market_result.get("success") and mtok:
                save_session_market_token(str(session_id), mtok, mrefresh or None)
                result["market_access_token"] = mtok
                if mrefresh:
                    result["market_refresh_token"] = mrefresh
            if market_result and market_result.get("success"):
                user_blob = extract_market_user_blob(market_result)
                market_uid: int | None = None
                if user_blob.get("id") is not None:
                    market_uid = int(user_blob["id"])
                company_brand = company_brand_from_user_blob(user_blob)
                persist_session_account_meta(
                    str(session_id),
                    account_kind=account_kind,
                    company_brand=company_brand,
                    market_user_id=market_uid,
                    market_is_admin=bool(market_result.get("is_market_admin")),
                    market_is_enterprise=bool(market_result.get("is_enterprise")),
                )
                result["account_kind"] = account_kind
                result["company_brand"] = company_brand
                result["market_is_admin"] = bool(market_result.get("is_market_admin"))
                result["market_is_enterprise"] = bool(market_result.get("is_enterprise"))

            if sku == "enterprise" and market_result and market_result.get("success") and mtok:
                from app.enterprise.mod_entitlements import (
                    get_cached_entitled_client_mod_ids,
                    persist_entitlements_to_session_row,
                    refresh_session_entitlements_from_market,
                    reload_enterprise_mods_after_login,
                )

                market_uid: int | None = None
                raw_login = market_result.get("raw")
                if isinstance(raw_login, dict):
                    ub = raw_login.get("user")
                    if isinstance(ub, dict) and ub.get("id") is not None:
                        market_uid = int(ub["id"])
                client_ids = await refresh_session_entitlements_from_market(
                    market_token=mtok,
                    market_user_id=market_uid,
                    market_username=username,
                    session_id=str(session_id),
                )
                persist_entitlements_to_session_row(str(session_id), client_ids)
                await reload_enterprise_mods_after_login()
                cached = get_cached_entitled_client_mod_ids()
                if cached is not None:
                    result["entitled_mod_ids"] = sorted(cached)
            if market_result:
                result["market_account"] = {
                    "success": bool(market_result.get("success")),
                    "market_base_url": market_result.get("market_base_url"),
                    "message": market_result.get("message", ""),
                    "is_enterprise": bool(market_result.get("is_enterprise")),
                    "is_market_admin": bool(market_result.get("is_market_admin")),
                }
        except Exception as exc:
            result["market_account"] = {
                "success": False,
                "message": f"市场账号自动同步失败：{exc}",
            }
        if session_id and "entitled_mod_ids" not in result:
            try:
                from app.enterprise.account_mod_binding import (
                    augment_entitled_client_mod_ids_for_username,
                )
                from app.enterprise.mod_entitlements import (
                    enterprise_mod_filter_active,
                    get_cached_entitled_client_mod_ids,
                    persist_entitlements_to_session_row,
                    reload_enterprise_mods_after_login,
                    set_session_entitlements,
                )

                fallback = augment_entitled_client_mod_ids_for_username(username, set())
                if fallback:
                    set_session_entitlements(
                        market_user_id=None,
                        market_username=username,
                        entitled_client_mod_ids=fallback,
                    )
                    persist_entitlements_to_session_row(str(session_id), fallback)
                    if enterprise_mod_filter_active():
                        await reload_enterprise_mods_after_login()
                    cached = get_cached_entitled_client_mod_ids()
                    if cached:
                        result["entitled_mod_ids"] = sorted(cached)
            except Exception:
                logger.exception("account_mod_binding fallback on login failed")
    resp = JSONResponse(result)
    if session_id:
        cookie_name = os.environ.get("SESSION_COOKIE_NAME", "session_id")
        max_age = int(os.environ.get("SESSION_COOKIE_MAX_AGE", "315360000"))
        resp.set_cookie(
            key=cookie_name,
            value=session_id,
            max_age=max_age,
            httponly=os.environ.get("SESSION_COOKIE_HTTPONLY", "1") not in ("0", "false", "False"),
            secure=os.environ.get("SESSION_COOKIE_SECURE", "").lower() in ("1", "true", "yes"),
            samesite=os.environ.get("SESSION_COOKIE_SAMESITE", "Lax"),
            path="/",
        )
    return resp


@router.get("/api/auth/profile")
def auth_profile_get(user=Depends(get_logged_in_user)):
    """当前用户个人资料（展示名、邮箱、头像）。"""
    return {"success": True, "data": {"user": _user_public_dict(user)}}


@router.patch("/api/auth/profile")
def auth_profile_patch(body: dict = Body(default_factory=dict), user=Depends(get_logged_in_user)):
    """更新当前用户展示名与邮箱。"""
    from app.application.user_app_service import get_user_app_service

    display_name = body.get("display_name")
    email = body.get("email")
    kwargs: dict[str, Any] = {}
    if display_name is not None:
        kwargs["display_name"] = str(display_name).strip()[:64]
    if email is not None:
        kwargs["email"] = str(email).strip()[:128]
    if not kwargs:
        return JSONResponse(
            {"success": False, "error": {"code": "INVALID_INPUT", "message": "无有效字段"}},
            status_code=400,
        )
    result = get_user_app_service().update_user(user.id, **kwargs)
    if not result.get("success"):
        return JSONResponse(
            {
                "success": False,
                "error": {"code": "UPDATE_FAILED", "message": result.get("message", "更新失败")},
            },
            status_code=400,
        )
    from app.db.models.user import User
    from app.db.session import get_db

    with get_db() as db:
        row = db.query(User).filter(User.id == user.id).first()
        if row is None:
            return JSONResponse(
                {"success": False, "error": {"code": "NOT_FOUND", "message": "用户不存在"}},
                status_code=404,
            )
        payload = _user_public_dict(row)
    return {"success": True, "data": {"user": payload}}


@router.post("/api/auth/profile/avatar")
async def auth_profile_avatar_upload(
    file: UploadFile | None = File(default=None),
    user=Depends(get_logged_in_user),
):
    """上传并替换当前用户头像（png/jpg/gif/webp，≤4MB）。"""
    if file is None or not file.filename:
        return JSONResponse(
            {"success": False, "error": {"code": "INVALID_INPUT", "message": "请选择图片文件"}},
            status_code=400,
        )
    from app.utils.secure_filename import secure_filename
    from app.utils.user_avatar_storage import (
        AVATAR_API_PATH,
        save_user_avatar_file,
    )

    safe_name = secure_filename(file.filename) or "avatar.png"
    ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else "png"
    content = await file.read()
    try:
        save_user_avatar_file(user.id, content, ext)
    except ValueError as exc:
        return JSONResponse(
            {"success": False, "error": {"code": "INVALID_FILE", "message": str(exc)}},
            status_code=400,
        )
    except OSError as exc:
        logger.exception("avatar save failed user_id=%s", user.id)
        return JSONResponse(
            {
                "success": False,
                "error": {"code": "SAVE_FAILED", "message": f"头像保存失败：{exc}"},
            },
            status_code=500,
        )

    from app.db.models.user import User
    from app.db.session import get_db

    with get_db() as db:
        row = db.query(User).filter(User.id == user.id).first()
        if row is not None:
            row.wx_avatar_url = AVATAR_API_PATH
    return {
        "success": True,
        "data": {"avatar_url": AVATAR_API_PATH},
    }


@router.get("/api/auth/avatar")
def auth_profile_avatar_get(user=Depends(get_logged_in_user)):
    """返回当前登录用户的头像文件（依赖会话 Cookie 或 Bearer）。"""
    from app.utils.user_avatar_storage import avatar_file_for_user, media_type_for_path

    path = avatar_file_for_user(user.id)
    if path is None:
        return JSONResponse(status_code=404, content={"success": False, "message": "未设置头像"})
    return FileResponse(str(path), media_type=media_type_for_path(path))


@router.post("/api/auth/company-brand")
async def auth_update_company_brand(
    request: Request, body: dict = Body(default_factory=dict), user=Depends(get_logged_in_user)
):
    """更新企业品牌名（写入 session，并同步修茈市场 user.company）。"""
    brand = str(body.get("company_brand") or body.get("company") or "").strip()[:256]
    sid = session_id_from_request(request)
    if not sid:
        return JSONResponse(
            {"success": False, "error": {"code": "NO_SESSION", "message": "无会话"}},
            status_code=400,
        )
    from app.application.session_account_meta import (
        load_session_account_meta,
        persist_session_account_meta,
    )
    from app.fastapi_routes.market_account import _proxy_json, resolve_valid_market_access_token

    meta = load_session_account_meta(sid) or {}
    persist_session_account_meta(
        sid,
        account_kind=str(meta.get("account_kind") or "enterprise"),
        company_brand=brand,
        market_user_id=meta.get("market_user_id"),
        market_is_admin=bool(meta.get("market_is_admin")),
        market_is_enterprise=bool(meta.get("market_is_enterprise")),
        impersonating_market_user_id=meta.get("impersonating_market_user_id"),
        impersonating_username=str(meta.get("impersonating_username") or ""),
    )
    tok = await resolve_valid_market_access_token(sid)
    if tok:
        auth = tok if tok.lower().startswith("bearer ") else f"Bearer {tok}"
        await _proxy_json(
            "PUT",
            "/api/auth/profile",
            json_body={"company": brand},
            authorization=auth,
            return_error_payload=True,
        )
    return {"success": True, "company_brand": brand}


@router.post("/api/auth/logout")
def auth_logout(request: Request):
    from app.application.auth_app_service import get_auth_app_service
    from app.fastapi_routes.market_account import clear_session_market_token

    sid = session_id_from_request(request)
    if not sid:
        return JSONResponse(
            {"success": False, "error": {"code": "NO_SESSION", "message": "无有效会话"}},
            status_code=400,
        )
    auth_app_service = get_auth_app_service()
    result = auth_app_service.logout(sid)
    clear_session_market_token(sid)
    try:
        from app.enterprise.mod_entitlements import clear_session_entitlements

        clear_session_entitlements()
    except Exception:
        pass
    resp = JSONResponse(result)
    cookie_name = os.environ.get("SESSION_COOKIE_NAME", "session_id")
    resp.delete_cookie(cookie_name, path="/")
    return resp


@router.post("/api/auth/password/change")
def auth_password_change(body: dict = Body(default_factory=dict), user=Depends(get_logged_in_user)):
    from app.application.auth_app_service import get_auth_app_service

    old_password = body.get("old_password", "")
    new_password = body.get("new_password", "")
    if not old_password or not new_password:
        return JSONResponse(
            {"success": False, "error": {"code": "INVALID_INPUT", "message": "请填写完整信息"}},
            status_code=400,
        )
    if len(new_password) < 6:
        return JSONResponse(
            {
                "success": False,
                "error": {"code": "WEAK_PASSWORD", "message": "新密码至少 6 个字符"},
            },
            status_code=400,
        )
    auth_app_service = get_auth_app_service()
    result = auth_app_service.change_password(user.id, old_password, new_password)
    if not result["success"]:
        return JSONResponse(result, status_code=400)
    return result


@router.get("/api/users")
def users_list(include_inactive: str = Query(default="false"), _user=Depends(_require_admin)):
    from app.application import get_user_app_service

    user_service = get_user_app_service()
    users = user_service.list_users(skip=0, limit=100)
    if include_inactive.lower() != "true":
        users = [u for u in users if u.get("is_active", True)]
    return {"success": True, "data": {"users": users, "count": len(users)}}


@router.get("/api/users/{user_id}")
def users_get(user_id: int, _user=Depends(_require_admin)):
    from app.application import get_user_app_service

    user_service = get_user_app_service()
    user = user_service.get_user(user_id)
    if not user:
        return JSONResponse(
            {"success": False, "error": {"code": "NOT_FOUND", "message": "用户不存在"}},
            status_code=404,
        )
    return {"success": True, "data": {"user": user}}


@router.post("/api/users")
def users_create(body: dict = Body(default_factory=dict), _user=Depends(_require_admin)):
    from app.application import get_user_app_service

    username = (body.get("username") or "").strip()
    password = body.get("password", "")
    if not username or not password:
        return JSONResponse(
            {
                "success": False,
                "error": {"code": "INVALID_INPUT", "message": "用户名和密码不能为空"},
            },
            status_code=400,
        )
    if len(password) < 6:
        return JSONResponse(
            {"success": False, "error": {"code": "WEAK_PASSWORD", "message": "密码至少6个字符"}},
            status_code=400,
        )
    role = body.get("role", "viewer")
    if role not in ["viewer", "operator", "admin"]:
        return JSONResponse(
            {"success": False, "error": {"code": "INVALID_ROLE", "message": "无效的角色"}},
            status_code=400,
        )
    user_service = get_user_app_service()
    result = user_service.create_user(
        username=username,
        password=password,
        display_name=body.get("display_name", ""),
        email=body.get("email", ""),
        role=role,
    )
    if not result["success"]:
        return JSONResponse(
            {"success": False, "error": {"code": "CREATE_FAILED", "message": result["error"]}},
            status_code=400,
        )
    return JSONResponse({"success": True, "data": {"user": result["user"]}}, status_code=201)


@router.put("/api/users/{user_id}")
def users_update(
    user_id: int, body: dict = Body(default_factory=dict), _user=Depends(_require_admin)
):
    from app.application import get_user_app_service

    role = body.get("role")
    if role and role not in ["viewer", "operator", "admin"]:
        return JSONResponse(
            {"success": False, "error": {"code": "INVALID_ROLE", "message": "无效的角色"}},
            status_code=400,
        )
    user_service = get_user_app_service()
    result = user_service.update_user(
        user_id=user_id,
        display_name=body.get("display_name"),
        email=body.get("email"),
        role=role,
        is_active=body.get("is_active"),
    )
    if not result["success"]:
        return JSONResponse(
            {"success": False, "error": {"code": "UPDATE_FAILED", "message": result["error"]}},
            status_code=400,
        )
    return {"success": True, "data": {"user": result["user"]}}


@router.delete("/api/users/{user_id}")
def users_delete(user_id: int, user=Depends(_require_admin)):
    if user.id == user_id:
        return JSONResponse(
            {"success": False, "error": {"code": "SELF_DELETE", "message": "不能删除自己"}},
            status_code=400,
        )
    from app.application import get_user_app_service

    user_service = get_user_app_service()
    result = user_service.delete_user(user_id)
    if not result.get("success"):
        return JSONResponse(result, status_code=400)
    return result


@router.post("/api/users/{user_id}/reset-password")
def users_reset_password(
    user_id: int, body: dict = Body(default_factory=dict), _user=Depends(_require_admin)
):
    from app.application.auth_app_service import get_auth_app_service

    new_password = body.get("new_password", "")
    if not new_password:
        return JSONResponse(
            {"success": False, "error": {"code": "MISSING_PASSWORD", "message": "新密码不能为空"}},
            status_code=400,
        )
    if len(new_password) < 6:
        return JSONResponse(
            {"success": False, "error": {"code": "WEAK_PASSWORD", "message": "密码至少6个字符"}},
            status_code=400,
        )
    auth_app_service = get_auth_app_service()
    result = auth_app_service.reset_password(user_id, new_password)
    if not result["success"]:
        return JSONResponse(result, status_code=400)
    return result
