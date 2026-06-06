"""Bridge XCAGI local UI to the Xiuci market account APIs."""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from typing import Any

import httpx
from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/market", tags=["market-account"])
logger = logging.getLogger(__name__)
_MARKET_SESSION_TOKENS: dict[str, str] = {}
_MARKET_SESSION_REFRESH_TOKENS: dict[str, str] = {}


def _market_base_url() -> str:
    return (os.environ.get("XCAGI_MARKET_BASE_URL") or "http://127.0.0.1:8765").strip().rstrip("/")


def _auth_header(raw: str) -> str:
    token = (raw or "").strip()
    if token.lower().startswith("authorization:"):
        token = token.split(":", 1)[1].strip()
    if token and not token.lower().startswith("bearer "):
        token = f"Bearer {token}"
    return token


def session_id_from_request(request: Request) -> str:
    cookie_name = os.environ.get("SESSION_COOKIE_NAME", "session_id")
    return str(
        request.cookies.get(cookie_name) or request.headers.get("X-Session-ID") or ""
    ).strip()


def bind_market_auth_to_session(
    request: Request,
    market_result: dict[str, Any],
) -> tuple[str, str]:
    """Write market JWT from ``login_market_with_password`` (or register) onto the current FHD session."""
    token = str(market_result.get("token") or "").strip()
    refresh = str(market_result.get("refresh_token") or "").strip()
    if token:
        save_session_market_token(session_id_from_request(request), token, refresh or None)
    return token, refresh


def save_session_market_token(
    session_id: str,
    token: str,
    refresh_token: str | None = None,
) -> None:
    sid = (session_id or "").strip()
    tok = (token or "").strip()
    if not sid or not tok:
        return
    _MARKET_SESSION_TOKENS[sid] = tok
    rtok = (refresh_token or "").strip()
    if rtok:
        _MARKET_SESSION_REFRESH_TOKENS[sid] = rtok
    try:
        from app.db.models.user import Session as UserSession
        from app.db.session import get_db

        with get_db() as db:
            row = db.query(UserSession).filter(UserSession.session_id == sid).first()
            if row is not None:
                row.market_access_token = tok
                if rtok:
                    row.market_refresh_token = rtok
                db.commit()
    except Exception:
        logger.exception(
            "save_session_market_token: failed to persist market token for session_id=%s", sid
        )


def clear_session_market_token(session_id: str) -> None:
    sid = (session_id or "").strip()
    if sid:
        _MARKET_SESSION_TOKENS.pop(sid, None)
        _MARKET_SESSION_REFRESH_TOKENS.pop(sid, None)
    try:
        from app.db.models.user import Session as UserSession
        from app.db.session import get_db

        with get_db() as db:
            row = db.query(UserSession).filter(UserSession.session_id == sid).first()
            if row is not None:
                if getattr(row, "market_access_token", None):
                    row.market_access_token = None
                if getattr(row, "market_refresh_token", None):
                    row.market_refresh_token = None
                db.commit()
    except Exception:
        logger.exception(
            "clear_session_market_token: failed to clear persisted token for session_id=%s", sid
        )


def session_market_token(session_id: str) -> str:
    sid = (session_id or "").strip()
    if not sid:
        return ""
    mem = _MARKET_SESSION_TOKENS.get(sid, "").strip()
    if mem:
        return mem
    try:
        from app.db.models.user import Session as UserSession
        from app.db.session import get_db

        with get_db() as db:
            row = db.query(UserSession).filter(UserSession.session_id == sid).first()
            raw = getattr(row, "market_access_token", None) if row is not None else None
            t = (raw or "").strip() if raw is not None else ""
            if t:
                _MARKET_SESSION_TOKENS[sid] = t
                return t
    except Exception:
        logger.exception("session_market_token: DB read failed for session_id=%s", sid)
    return ""


def session_market_refresh_token(session_id: str) -> str:
    sid = (session_id or "").strip()
    if not sid:
        return ""
    mem = _MARKET_SESSION_REFRESH_TOKENS.get(sid, "").strip()
    if mem:
        return mem
    try:
        from app.db.models.user import Session as UserSession
        from app.db.session import get_db

        with get_db() as db:
            row = db.query(UserSession).filter(UserSession.session_id == sid).first()
            raw = getattr(row, "market_refresh_token", None) if row is not None else None
            t = (raw or "").strip() if raw is not None else ""
            if t:
                _MARKET_SESSION_REFRESH_TOKENS[sid] = t
                return t
    except Exception:
        logger.exception("session_market_refresh_token: DB read failed for session_id=%s", sid)
    return ""


def latest_session_market_refresh_token() -> str:
    try:
        from app.db.models.user import Session as UserSession
        from app.db.session import get_db

        with get_db() as db:
            rows = (
                db.query(UserSession)
                .filter(UserSession.market_refresh_token.isnot(None))
                .order_by(UserSession.created_at.desc())
                .limit(10)
                .all()
            )
            for row in rows:
                tok = str(getattr(row, "market_refresh_token", "") or "").strip()
                if tok:
                    return tok
    except Exception:
        logger.exception("latest_session_market_refresh_token: DB read failed")
    return ""


def latest_session_market_token() -> str:
    """Desktop fallback: use the newest persisted market token when browser cookies are unavailable.

    LAN/IP access can miss the ``session_id`` cookie even though the local single-user desktop
    session has a freshly persisted market token from login. Prefer that over stale localStorage
    tokens sent by the SPA.
    """
    try:
        from app.db.models.user import Session as UserSession
        from app.db.session import get_db

        with get_db() as db:
            rows = (
                db.query(UserSession)
                .filter(UserSession.market_access_token.isnot(None))
                .order_by(UserSession.created_at.desc())
                .limit(10)
                .all()
            )
            for row in rows:
                tok = str(getattr(row, "market_access_token", "") or "").strip()
                if tok:
                    return tok
    except Exception:
        logger.exception("latest_session_market_token: DB read failed")
    return ""


def _normalize_bearer_token(raw: str) -> str:
    """Strip ``Bearer `` prefix for consistent ``market_access_token`` JSON fields."""
    t = (raw or "").strip()
    if t.lower().startswith("bearer "):
        return t[7:].strip()
    return t


def _proxy_error_http_status(payload: Any) -> int | None:
    """Parse HTTP status from ``_proxy_json(..., return_error_payload=True)`` error dict."""
    if not isinstance(payload, dict) or not payload.get("__proxy_error__"):
        return None
    raw = payload.get("status_code")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


@router.get("/session-handoff")
async def market_session_handoff(request: Request):
    """Return the Xiuci market JWT bound to the current FHD session.

    Login stores this in-memory via ``save_session_market_token``; the SPA needs it in
    ``localStorage`` to append ``xcagi_mt=`` on cross-origin links (cookies do not carry).
    """
    try:
        from app.infrastructure.auth.dependencies import resolve_session_user

        user = resolve_session_user(request)
        if user is None:
            tok = _normalize_bearer_token(latest_session_market_token())
            if tok:
                return {
                    "success": True,
                    "data": {
                        "market_access_token": tok,
                        "market_base_url": _market_base_url(),
                    },
                }
            return JSONResponse(
                {
                    "success": False,
                    "message": (
                        "当前会话未绑定修茈市场账号。请使用与本软件相同的用户名与密码重新登录，"
                        "或在设置中粘贴修茈 Authorization 完成同步。"
                    ),
                },
                status_code=404,
            )
        sid = session_id_from_request(request)
        tok = await resolve_valid_market_access_token(sid)
        if not tok:
            tok = _normalize_bearer_token(latest_session_market_token())
            if tok:
                tok = await resolve_valid_market_access_token(sid)
        if not tok:
            return JSONResponse(
                {
                    "success": False,
                    "message": (
                        "当前会话未绑定修茈市场账号。请使用与本软件相同的用户名与密码重新登录，"
                        "或在设置中粘贴修茈 Authorization 完成同步。"
                    ),
                },
                status_code=404,
            )
        _ = user  # validated logged-in user
        refresh_out = session_market_refresh_token(sid) or latest_session_market_refresh_token()
        data: dict[str, Any] = {
            "market_access_token": tok,
            "market_base_url": _market_base_url(),
        }
        if refresh_out:
            data["market_refresh_token"] = refresh_out
        try:
            if sid:
                from app.enterprise.mod_entitlements import sync_entitlements_for_session

                await sync_entitlements_for_session(sid)
        except Exception:
            logger.exception("enterprise entitlements refresh on session-handoff failed")
        return {"success": True, "data": data}
    except Exception:
        logger.exception("market_session_handoff failed")
        sid = session_id_from_request(request)
        fallback_tok = _normalize_bearer_token(
            session_market_token(sid) or latest_session_market_token()
        )
        if fallback_tok:
            return {
                "success": True,
                "data": {
                    "market_access_token": fallback_tok,
                    "market_base_url": _market_base_url(),
                },
            }
        return JSONResponse(
            {
                "success": False,
                "message": (
                    "修茈市场会话交接暂时不可用，请稍后重试或检查 XCAGI_MARKET_BASE_URL 与市场服务状态。"
                ),
                "data": {"market_base_url": _market_base_url()},
            },
            status_code=502,
        )


def _authorization_from_request(request: Request, body: dict[str, Any]) -> str:
    """Current desktop session token → newest persisted token → explicit browser token.

    The browser may keep an old market JWT in localStorage while the local backend already has
    a fresh token bound to the current FHD login session. Strong account state should follow the
    backend session, not stale client storage.
    """
    session_auth = _auth_header(session_market_token(session_id_from_request(request)))
    if session_auth:
        return session_auth
    latest_auth = _auth_header(latest_session_market_token())
    if latest_auth:
        return latest_auth
    auth = _auth_header(str(body.get("authorization") or body.get("token") or ""))
    if auth:
        return auth
    hdr = str(
        request.headers.get("Authorization") or request.headers.get("authorization") or ""
    ).strip()
    if hdr:
        return _auth_header(hdr)
    return ""


async def _authorization_from_request_resolved(request: Request, body: dict[str, Any]) -> str:
    """Like ``_authorization_from_request`` but refreshes expired session-bound market JWTs."""
    sid = session_id_from_request(request)
    session_tok = _normalize_bearer_token(
        session_market_token(sid) or latest_session_market_token()
    )
    if session_tok:
        resolved = await resolve_valid_market_access_token(sid)
        if resolved:
            return _auth_header(resolved)
    return _authorization_from_request(request, body)


def _body_snippet(payload: Any, limit: int = 240) -> str:
    if isinstance(payload, dict):
        try:
            import json as _json

            text = _json.dumps(payload, ensure_ascii=False)
        except Exception:
            text = str(payload)
    else:
        text = str(payload or "")
    text = text.replace("\n", " ").strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def _error_message(payload: Any, status_code: int) -> str:
    base = _market_base_url()
    if isinstance(payload, dict):
        detail = payload.get("detail") or payload.get("message") or payload.get("error")
        if isinstance(detail, list):
            msg = "; ".join(str(x.get("msg") if isinstance(x, dict) else x) for x in detail)
        elif detail:
            msg = str(detail)
        else:
            msg = ""
        if status_code >= 500:
            hint = f"请检查 XCAGI_MARKET_BASE_URL={base}"
            if msg and not re.match(r"^internal server error$", msg, re.I):
                return f"市场服务返回 {status_code}：{msg}。{hint}"
            return f"市场服务返回 {status_code}（服务器内部错误）。{hint}"
        if msg:
            return msg
    if status_code >= 500:
        return f"市场服务返回 {status_code}（服务器内部错误）。请检查 XCAGI_MARKET_BASE_URL={base}"
    return f"HTTP {status_code}"


async def _proxy_json(
    method: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
    authorization: str = "",
    return_error_payload: bool = False,
):
    url = f"{_market_base_url()}{path}"
    headers: dict[str, str] = {"Accept": "application/json"}
    if authorization:
        headers["Authorization"] = _auth_header(authorization)
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.request(method, url, json=json_body, headers=headers)
    except httpx.HTTPError as exc:
        return JSONResponse(
            {
                "success": False,
                "message": f"无法连接修茈市场服务器：{exc}",
                "data": {"market_base_url": _market_base_url()},
            },
            status_code=502,
        )
    except Exception as exc:
        logger.warning("_proxy_json transport error to %s: %s", url, exc)
        return JSONResponse(
            {
                "success": False,
                "message": f"无法连接修茈市场服务器：{exc}",
                "data": {"market_base_url": _market_base_url()},
            },
            status_code=502,
        )
    try:
        payload = res.json()
    except ValueError:
        payload = {"detail": res.text}
    if res.status_code >= 400:
        if res.status_code >= 500:
            logger.warning(
                "market proxy %s %s -> %s body=%s",
                method,
                url,
                res.status_code,
                _body_snippet(payload),
            )
        if return_error_payload:
            return {"__proxy_error__": True, "status_code": res.status_code, "payload": payload}
        detail = _error_message(payload, res.status_code)
        return JSONResponse(
            {
                "success": False,
                "message": str(detail),
                "data": {
                    **(payload if isinstance(payload, dict) else {}),
                    "market_base_url": _market_base_url(),
                },
            },
            status_code=res.status_code,
        )
    return payload


def _token_from_auth_response(payload: Any) -> str:
    """Extract access JWT from market ``POST /api/auth/login`` JSON (several response shapes)."""
    if not isinstance(payload, dict):
        return ""
    inner = payload.get("data") if isinstance(payload.get("data"), dict) else None
    candidates: list[Any] = []
    if inner:
        candidates.extend(
            [
                inner.get("access_token"),
                inner.get("token"),
                inner.get("market_access_token"),
            ]
        )
        nested = inner.get("tokens") if isinstance(inner.get("tokens"), dict) else None
        if nested:
            candidates.extend([nested.get("access_token"), nested.get("accessToken")])
    candidates.extend(
        [
            payload.get("access_token"),
            payload.get("token"),
            payload.get("market_access_token"),
        ]
    )
    nested_top = payload.get("tokens") if isinstance(payload.get("tokens"), dict) else None
    if nested_top:
        candidates.extend([nested_top.get("access_token"), nested_top.get("accessToken")])
    for c in candidates:
        if c is None:
            continue
        s = str(c).strip()
        if s:
            return s
    return ""


def _refresh_token_from_auth_response(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    inner = payload.get("data") if isinstance(payload.get("data"), dict) else None
    candidates: list[Any] = []
    if inner:
        candidates.extend([inner.get("refresh_token"), inner.get("refreshToken")])
        nested = inner.get("tokens") if isinstance(inner.get("tokens"), dict) else None
        if nested:
            candidates.extend([nested.get("refresh_token"), nested.get("refreshToken")])
    candidates.extend([payload.get("refresh_token"), payload.get("refreshToken")])
    nested_top = payload.get("tokens") if isinstance(payload.get("tokens"), dict) else None
    if nested_top:
        candidates.extend([nested_top.get("refresh_token"), nested_top.get("refreshToken")])
    for c in candidates:
        if c is None:
            continue
        s = str(c).strip()
        if s:
            return s
    return ""


def _user_blob_from_market_payload(payload: Any) -> dict[str, Any]:
    """从市场 login/me 等多种 JSON 形态提取 user 字典。"""
    if not isinstance(payload, dict):
        return {}
    if isinstance(payload.get("user"), dict):
        return dict(payload["user"])
    data = payload.get("data")
    if isinstance(data, dict):
        if isinstance(data.get("user"), dict):
            return dict(data["user"])
        if data.get("id") is not None and data.get("username"):
            return dict(data)
    if payload.get("id") is not None and payload.get("username"):
        return dict(payload)
    return {}


def _market_identity_from_payloads(*payloads: Any) -> tuple[bool, bool, dict[str, Any]]:
    """合并 login + /me 响应，得到 (is_enterprise, is_market_admin, user_blob)。"""
    is_enterprise = False
    is_market_admin = False
    user_blob: dict[str, Any] = {}
    for payload in payloads:
        if isinstance(payload, dict) and payload.get("__proxy_error__"):
            continue
        blob = _user_blob_from_market_payload(payload)
        if not blob:
            continue
        if not user_blob:
            user_blob = blob
        if "is_enterprise" in blob:
            is_enterprise = bool(blob.get("is_enterprise"))
        if "is_admin" in blob:
            is_market_admin = bool(blob.get("is_admin"))
    return is_enterprise, is_market_admin, user_blob


async def refresh_session_market_token(session_id: str) -> str:
    """Use persisted modstore refresh_token to obtain a new access_token."""
    sid = (session_id or "").strip()
    refresh = session_market_refresh_token(sid) or latest_session_market_refresh_token()
    if not refresh:
        return ""
    payload = await _proxy_json(
        "POST",
        "/api/auth/refresh",
        json_body={"refresh_token": refresh},
        return_error_payload=True,
    )
    if isinstance(payload, JSONResponse):
        return ""
    if isinstance(payload, dict) and payload.get("__proxy_error__"):
        return ""
    access = _token_from_auth_response(payload)
    new_refresh = _refresh_token_from_auth_response(payload) or refresh
    if access and sid:
        save_session_market_token(sid, access, new_refresh)
    return access


async def resolve_valid_market_access_token(session_id: str) -> str:
    """Return a working market access token, refreshing when /api/auth/me returns 401."""
    sid = (session_id or "").strip()
    tok = _normalize_bearer_token(session_market_token(sid) or latest_session_market_token())
    if not tok:
        return ""
    me = await _proxy_json(
        "GET", "/api/auth/me", authorization=f"Bearer {tok}", return_error_payload=True
    )
    if isinstance(me, JSONResponse):
        logger.warning(
            "market unreachable during token validation (session_id=%s), using local token",
            sid[:8] if sid else "",
        )
        return tok
    if isinstance(me, dict) and me.get("__proxy_error__"):
        if _proxy_error_http_status(me) == 401:
            refreshed = await refresh_session_market_token(sid)
            return _normalize_bearer_token(refreshed)
        logger.warning(
            "market /api/auth/me error status=%s, using local token",
            me.get("status_code"),
        )
        return tok
    return tok


def _looks_like_verification_required(payload: Any) -> bool:
    msg = _error_message(payload, 400)
    return bool(re.search(r"验证码|verification|code", msg, re.I))


async def _register_without_verification(username: str, password: str, email: str):
    """Use the server-side open registration API when the normal market form requires email code."""
    payload = await _proxy_json(
        "POST",
        "/api/market/open/register",
        json_body={"username": username, "password": password, "email": email},
        return_error_payload=True,
    )
    if isinstance(payload, dict) and payload.get("__proxy_error__"):
        payload = await _proxy_json(
            "POST",
            "/api/auth/register-open",
            json_body={"username": username, "password": password, "email": email},
            return_error_payload=True,
        )
    return payload


async def send_market_reset_password_code(email: str) -> dict[str, Any]:
    """Request password-reset verification email from the configured market server."""
    email_norm = (email or "").strip().lower()
    if not email_norm or "@" not in email_norm:
        return {"success": False, "message": "请填写有效邮箱"}
    payload = await _proxy_json(
        "POST",
        "/api/auth/send-reset-password-code",
        json_body={"email": email_norm},
        return_error_payload=True,
    )
    if isinstance(payload, JSONResponse):
        return {"success": False, "message": "市场服务不可用"}
    if isinstance(payload, dict) and payload.get("__proxy_error__"):
        status_code = int(payload.get("status_code") or 502)
        raw = payload.get("payload")
        return {
            "success": False,
            "message": _error_message(raw, status_code) or "无法连接修茈市场发送验证码",
            "market_base_url": _market_base_url(),
        }
    msg = ""
    if isinstance(payload, dict):
        msg = str(payload.get("message") or "").strip()
    return {
        "success": True,
        "message": msg or "若该邮箱已注册，将收到验证码邮件",
        "market_base_url": _market_base_url(),
        "raw": payload,
    }


async def reset_market_password_with_code(
    email: str, code: str, new_password: str
) -> dict[str, Any]:
    """Reset password on market server using email verification code."""
    email_norm = (email or "").strip().lower()
    code_s = (code or "").strip()
    if not email_norm or "@" not in email_norm:
        return {"success": False, "message": "请填写有效邮箱"}
    if len(code_s) < 4:
        return {"success": False, "message": "请填写验证码"}
    if len(new_password or "") < 6:
        return {"success": False, "message": "新密码至少 6 个字符"}
    payload = await _proxy_json(
        "POST",
        "/api/auth/reset-password",
        json_body={"email": email_norm, "code": code_s, "new_password": new_password},
        return_error_payload=True,
    )
    if isinstance(payload, JSONResponse):
        return {"success": False, "message": "市场服务不可用"}
    if isinstance(payload, dict) and payload.get("__proxy_error__"):
        status_code = int(payload.get("status_code") or 400)
        raw = payload.get("payload")
        return {
            "success": False,
            "message": _error_message(raw, status_code) or "重置失败",
            "raw": raw,
        }
    if isinstance(payload, dict) and payload.get("ok") is False:
        return {
            "success": False,
            "message": str(payload.get("message") or payload.get("detail") or "重置失败"),
            "raw": payload,
        }
    return {
        "success": True,
        "message": "密码已重置",
        "raw": payload,
    }


async def register_market_user(
    username: str,
    password: str,
    email: str,
    verification_code: str = "",
) -> dict[str, Any]:
    """Register on the configured Xiuci market server. Returns success/message/token/raw."""
    register_body = {
        "username": username,
        "password": password,
        "email": email,
        "verification_code": (verification_code or "").strip() or "000000",
    }
    payload = await _proxy_json(
        "POST", "/api/auth/register", json_body=register_body, return_error_payload=True
    )
    if isinstance(payload, JSONResponse):
        return {"success": False, "message": "市场服务不可用"}
    if isinstance(payload, dict) and payload.get("__proxy_error__"):
        status_code = int(payload.get("status_code") or 400)
        raw_error = payload.get("payload")
        if not verification_code and _looks_like_verification_required(raw_error):
            payload = await _register_without_verification(username, password, email)
            if isinstance(payload, dict) and payload.get("__proxy_error__"):
                status_code = int(payload.get("status_code") or 400)
                raw_error = payload.get("payload")
            else:
                status_code = 200
        if status_code >= 400:
            return {
                "success": False,
                "message": _error_message(raw_error, status_code),
                "raw": raw_error,
            }
    token = _token_from_auth_response(payload)
    refresh = _refresh_token_from_auth_response(payload)
    return {
        "success": True,
        "message": "",
        "token": token,
        "refresh_token": refresh,
        "raw": payload,
        "market_base_url": _market_base_url(),
    }


@router.post("/register")
async def market_register(request: Request, body: dict[str, Any] = Body(default_factory=dict)):
    """Register a Xiuci market account through the configured market server."""
    username = str(body.get("username") or "").strip()
    password = str(body.get("password") or "")
    email = str(body.get("email") or "").strip()
    verification_code = str(body.get("verification_code") or body.get("code") or "").strip()
    if not username or not password or not email:
        return JSONResponse(
            {"success": False, "message": "username、password、email 必填"}, status_code=400
        )
    result = await register_market_user(username, password, email, verification_code)
    if not result.get("success"):
        return JSONResponse(
            {
                "success": False,
                "message": result.get("message", "注册失败"),
                "data": result.get("raw"),
            },
            status_code=400,
        )
    token, _ = bind_market_auth_to_session(request, result)
    return {
        "success": True,
        "data": {
            "market_base_url": result.get("market_base_url"),
            "token": token,
            "raw": result.get("raw"),
        },
    }


@router.post("/login")
async def market_login(request: Request, body: dict[str, Any] = Body(default_factory=dict)):
    """Login to Xiuci market (username/password) and bind JWT to the current FHD session.

    Prefer ``POST /api/auth/login`` for the desktop app; this route remains for
    settings/tools that only need market credentials. Token-only bind: ``POST /account-sync``.
    """
    username = str(body.get("username") or body.get("email") or "").strip()
    password = str(body.get("password") or "")
    if not username or not password:
        return JSONResponse(
            {"success": False, "message": "username 与 password 必填"}, status_code=400
        )
    market_result = await login_market_with_password(username, password)
    if not market_result.get("success"):
        return JSONResponse(
            {"success": False, "message": market_result.get("message", "市场登录失败")},
            status_code=403,
        )
    token, refresh = bind_market_auth_to_session(request, market_result)
    return {
        "success": True,
        "data": {
            "market_base_url": _market_base_url(),
            "token": token,
            "raw": market_result.get("raw"),
        },
    }


async def login_market_with_password(username: str, password: str) -> dict[str, Any]:
    """Authenticate against the market server and return a normalized token payload."""
    payload = await _proxy_json(
        "POST", "/api/auth/login", json_body={"username": username, "password": password}
    )
    if isinstance(payload, JSONResponse):
        try:
            raw_body = json.loads(payload.body.decode("utf-8") if payload.body else "{}")
        except Exception:
            raw_body = {}
        message = (
            str(raw_body.get("message") or "").strip()
            or str(raw_body.get("detail") or "").strip()
            or _error_message(raw_body, int(payload.status_code or 502))
        )
        return {
            "success": False,
            "message": message,
            "status_code": int(payload.status_code or 502),
            "raw": raw_body,
            "market_base_url": _market_base_url(),
        }
    token = _token_from_auth_response(payload)
    refresh = _refresh_token_from_auth_response(payload)
    if not token:
        return {"success": False, "message": "市场登录成功但未返回 access_token", "raw": payload}
    me = await _proxy_json(
        "GET", "/api/auth/me", authorization=f"Bearer {token}", return_error_payload=True
    )
    is_enterprise, is_market_admin, user_blob = _market_identity_from_payloads(payload, me)
    raw_out = dict(payload) if isinstance(payload, dict) else {}
    if user_blob and not isinstance(raw_out.get("user"), dict):
        raw_out["user"] = user_blob
    return {
        "success": True,
        "market_base_url": _market_base_url(),
        "token": token,
        "refresh_token": refresh,
        "is_enterprise": is_enterprise,
        "is_market_admin": is_market_admin,
        "raw": raw_out,
    }


@router.post("/account-sync")
async def market_account_sync(request: Request, body: dict[str, Any] = Body(default_factory=dict)):
    authorization = _auth_header(str(body.get("authorization") or body.get("token") or ""))
    if not authorization:
        hdr = str(
            request.headers.get("Authorization") or request.headers.get("authorization") or ""
        ).strip()
        if hdr:
            authorization = _auth_header(hdr)
    if not authorization:
        return JSONResponse({"success": False, "message": "authorization 必填"}, status_code=400)
    payload = await _proxy_json("GET", "/api/auth/me", authorization=authorization)
    if isinstance(payload, JSONResponse):
        return payload
    save_session_market_token(
        session_id_from_request(request), _normalize_bearer_token(authorization)
    )
    data = (
        payload.get("data")
        if isinstance(payload, dict) and isinstance(payload.get("data"), dict)
        else payload
    )
    user = (
        data.get("user") if isinstance(data, dict) and isinstance(data.get("user"), dict) else data
    )
    return {"success": True, "data": {"user": user, "market_base_url": _market_base_url()}}


def _degraded_account_overview(message: str) -> dict[str, Any]:
    """Market unreachable — return 200 so SPA can still show wallet/plan links."""
    return {
        "degraded": True,
        "market_unreachable": True,
        "sync_warning": message,
        "user": {},
        "wallet": {"balance": None},
        "membership": {"label": "未同步", "tier": "unknown", "can_byok": False},
        "quotas": [],
        "llm": {"providers": []},
        "market_base_url": _market_base_url(),
    }


def _merge_live_overview_fields(data: dict[str, Any], live: dict[str, Any]) -> None:
    for key in ("wallet", "plan", "membership", "quotas"):
        if live.get(key) is not None:
            data[key] = live.get(key)
    if isinstance(live.get("llm"), dict):
        current_llm = data.get("llm") if isinstance(data.get("llm"), dict) else {}
        data["llm"] = {**current_llm, **live["llm"]}
    if live.get("user") is not None:
        data["user"] = live.get("user")


@router.post("/account-overview")
async def market_account_overview(
    request: Request, body: dict[str, Any] = Body(default_factory=dict)
):
    try:
        authorization = await _authorization_from_request_resolved(request, body)
    except Exception as exc:
        logger.exception("market_account_overview: resolve authorization failed")
        return {
            "success": True,
            "data": _degraded_account_overview(f"读取市场令牌失败：{exc}"),
        }
    if not authorization:
        return JSONResponse(
            {"success": False, "message": "尚未绑定市场账号；请重新登录软件以自动同步"},
            status_code=401,
        )
    try:
        payload = await _proxy_json(
            "GET", "/api/account/bootstrap", authorization=authorization, return_error_payload=True
        )
        data: dict[str, Any] | None = None
        sync_warning = ""

        if isinstance(payload, JSONResponse):
            try:
                import json as _json

                proxy_body = _json.loads(payload.body.decode() if payload.body else "{}")
                err = str(proxy_body.get("message") or proxy_body.get("detail") or "市场服务不可用")
            except Exception:
                err = "市场服务不可用"
            data = _degraded_account_overview(err)
            sync_warning = err
        elif isinstance(payload, dict) and not payload.get("__proxy_error__"):
            raw = payload.get("data") if isinstance(payload.get("data"), dict) else payload
            data = raw if isinstance(raw, dict) else None
            if isinstance(data, dict):
                live = await _legacy_account_overview(authorization)
                if isinstance(live, dict) and not live.get("__proxy_error__"):
                    _merge_live_overview_fields(data, live)
                elif isinstance(live, dict) and live.get("__proxy_error__"):
                    sync_warning = _error_message(
                        live.get("payload"), int(live.get("status_code") or 502)
                    )

        if data is None:
            legacy = await _legacy_account_overview(authorization)
            if isinstance(legacy, dict) and not legacy.get("__proxy_error__"):
                data = legacy
            else:
                err = ""
                if isinstance(legacy, dict) and legacy.get("__proxy_error__"):
                    err = _error_message(
                        legacy.get("payload"), int(legacy.get("status_code") or 502)
                    )
                elif isinstance(payload, dict) and payload.get("__proxy_error__"):
                    err = _error_message(
                        payload.get("payload"), int(payload.get("status_code") or 502)
                    )
                else:
                    err = "无法连接修茈市场服务器"
                data = _degraded_account_overview(err)
                logger.warning(
                    "market_account_overview degraded: %s (base=%s)", err, _market_base_url()
                )

        if not isinstance(data, dict):
            data = _degraded_account_overview("市场账户概览返回格式异常")

        data = {**data, "market_base_url": _market_base_url()}
        if sync_warning and not data.get("sync_warning"):
            data["sync_warning"] = sync_warning
        return {"success": True, "data": data}
    except Exception as exc:
        logger.exception("market_account_overview failed")
        return {
            "success": True,
            "data": _degraded_account_overview(f"账户概览异常：{exc}"),
        }


async def _market_llm_catalog_impl(request: Request, body: dict[str, Any]):
    authorization = await _authorization_from_request_resolved(request, body)
    if not authorization:
        return JSONResponse(
            {"success": False, "message": "尚未绑定市场账号；请重新登录软件以自动同步"},
            status_code=401,
        )
    refresh = "1" if bool(body.get("refresh")) else "0"
    payload = await _proxy_json(
        "GET",
        f"/api/llm/catalog?refresh={refresh}",
        authorization=authorization,
        return_error_payload=True,
    )
    if isinstance(payload, JSONResponse):
        return payload
    if isinstance(payload, dict) and payload.get("__proxy_error__"):
        status_code = int(payload.get("status_code") or 502)
        raw_error = payload.get("payload")
        msg = _error_message(raw_error, status_code)
        return {
            "success": True,
            "data": {
                "degraded": True,
                "providers": [],
                "sync_warning": msg,
                "market_base_url": _market_base_url(),
            },
        }
    if not isinstance(payload, dict):
        return {
            "success": True,
            "data": {
                "degraded": True,
                "providers": [],
                "sync_warning": "模型目录返回格式异常",
                "market_base_url": _market_base_url(),
            },
        }
    return {"success": True, "data": {**payload, "market_base_url": _market_base_url()}}


@router.post("/llm-catalog")
async def market_llm_catalog_post(
    request: Request, body: dict[str, Any] = Body(default_factory=dict)
):
    return await _market_llm_catalog_impl(request, body)


@router.get("/llm-catalog")
async def market_llm_catalog_get(request: Request, refresh: bool = False):
    return await _market_llm_catalog_impl(request, {"refresh": refresh})


async def _legacy_account_overview(authorization: str) -> dict[str, Any]:
    """Compose account overview from older market APIs when /api/account/bootstrap is not deployed."""
    me = await _proxy_json(
        "GET", "/api/auth/me", authorization=authorization, return_error_payload=True
    )
    if isinstance(me, dict) and me.get("__proxy_error__"):
        return me
    wallet = await _proxy_json(
        "GET", "/api/wallet/overview", authorization=authorization, return_error_payload=True
    )
    if isinstance(wallet, dict) and wallet.get("__proxy_error__"):
        balance = await _proxy_json(
            "GET", "/api/wallet/balance", authorization=authorization, return_error_payload=True
        )
        wallet_data = (
            {}
            if isinstance(balance, dict) and balance.get("__proxy_error__")
            else {"wallet": balance}
        )
    else:
        wallet_data = wallet if isinstance(wallet, dict) else {}
    plan = await _proxy_json(
        "GET", "/api/payment/my-plan", authorization=authorization, return_error_payload=True
    )
    plan_data = (
        {}
        if isinstance(plan, dict) and plan.get("__proxy_error__")
        else (plan if isinstance(plan, dict) else {})
    )
    llm = await _proxy_json(
        "GET", "/api/llm/status", authorization=authorization, return_error_payload=True
    )
    llm_data = (
        {}
        if isinstance(llm, dict) and llm.get("__proxy_error__")
        else (llm if isinstance(llm, dict) else {})
    )
    user = me.get("user") if isinstance(me, dict) and isinstance(me.get("user"), dict) else me
    wallet_obj = (
        wallet_data.get("wallet") if isinstance(wallet_data.get("wallet"), dict) else wallet_data
    )
    return {
        "ok": True,
        "user": user,
        "wallet": wallet_obj,
        "plan": plan_data.get("plan"),
        "membership": plan_data.get("membership"),
        "quotas": plan_data.get("quotas") or [],
        "llm": {
            "providers": llm_data.get("providers") or [],
            "fernet_configured": llm_data.get("fernet_configured"),
            "byok_configured_count": len(
                [p for p in (llm_data.get("providers") or []) if p.get("has_user_override")]
            ),
        },
    }


def _market_auth_from_request(request: Request) -> str:
    sid = session_id_from_request(request)
    tok = session_market_token(sid)
    if tok:
        return tok
    return str(request.headers.get("Authorization") or "").strip()


@router.get("/payment/plans")
async def market_payment_plans(request: Request):
    """修茈市场套餐（含微信/支付宝统一收银，Java SoT）。"""
    payload = await _proxy_json(
        "GET",
        "/api/payment/plans",
        authorization=_market_auth_from_request(request),
        return_error_payload=True,
    )
    if isinstance(payload, dict) and payload.get("__proxy_error__"):
        return JSONResponse(
            {
                "success": False,
                "message": _error_message(
                    payload.get("payload"), int(payload.get("status_code") or 502)
                ),
            },
            status_code=int(payload.get("status_code") or 502),
        )
    return {"success": True, "data": payload, "market_base_url": _market_base_url()}


@router.post("/payment/checkout")
async def market_payment_checkout(
    request: Request, body: dict[str, Any] = Body(default_factory=dict)
):
    payload = await _proxy_json(
        "POST",
        "/api/payment/checkout",
        json_body=body,
        authorization=_market_auth_from_request(request),
        return_error_payload=True,
    )
    if isinstance(payload, dict) and payload.get("__proxy_error__"):
        return JSONResponse(
            {
                "success": False,
                "message": _error_message(
                    payload.get("payload"), int(payload.get("status_code") or 502)
                ),
            },
            status_code=int(payload.get("status_code") or 502),
        )
    return {"success": True, "data": payload}


@router.get("/payment/orders")
async def market_payment_orders(
    request: Request,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    path = f"/api/payment/orders?limit={int(limit)}&offset={int(offset)}"
    if status:
        path += f"&status={status.strip()}"
    payload = await _proxy_json(
        "GET",
        path,
        authorization=_market_auth_from_request(request),
        return_error_payload=True,
    )
    if isinstance(payload, dict) and payload.get("__proxy_error__"):
        return JSONResponse(
            {
                "success": False,
                "message": _error_message(
                    payload.get("payload"), int(payload.get("status_code") or 502)
                ),
            },
            status_code=int(payload.get("status_code") or 502),
        )
    return {"success": True, "data": payload}


@router.get("/payment/query/{out_trade_no}")
async def market_payment_query(request: Request, out_trade_no: str):
    payload = await _proxy_json(
        "GET",
        f"/api/payment/query/{out_trade_no}",
        authorization=_market_auth_from_request(request),
        return_error_payload=True,
    )
    if isinstance(payload, dict) and payload.get("__proxy_error__"):
        return JSONResponse(
            {
                "success": False,
                "message": _error_message(
                    payload.get("payload"), int(payload.get("status_code") or 502)
                ),
            },
            status_code=int(payload.get("status_code") or 502),
        )
    return {"success": True, "data": payload}


@router.get("/wallet/overview")
async def market_wallet_overview(request: Request):
    payload = await _proxy_json(
        "GET",
        "/api/wallet/overview",
        authorization=_market_auth_from_request(request),
        return_error_payload=True,
    )
    if isinstance(payload, dict) and payload.get("__proxy_error__"):
        return JSONResponse(
            {
                "success": False,
                "message": _error_message(
                    payload.get("payload"), int(payload.get("status_code") or 502)
                ),
            },
            status_code=int(payload.get("status_code") or 502),
        )
    return {"success": True, "data": payload}


@router.get("/status")
async def market_status():
    """Check whether the local backend can reach the configured Xiuci market server."""
    payload = await _proxy_json("GET", "/api/health", return_error_payload=True)
    if isinstance(payload, JSONResponse):
        return payload
    reachable = not (isinstance(payload, dict) and payload.get("__proxy_error__"))
    return {
        "success": reachable,
        "data": {
            "market_base_url": _market_base_url(),
            "reachable": reachable,
            "raw": (
                payload.get("payload")
                if isinstance(payload, dict) and payload.get("__proxy_error__")
                else payload
            ),
        },
    }


@router.post("/dev-create-account")
async def market_dev_create_account(body: dict[str, Any] = Body(default_factory=dict)):
    """Create a market account via server-side open API and verify login/overview connectivity."""
    username = str(body.get("username") or f"xcagi_{uuid.uuid4().hex[:10]}").strip()
    password = str(body.get("password") or uuid.uuid4().hex[:12])
    email = str(body.get("email") or f"{username}@xcagi.local").strip()
    if len(password) < 6:
        return JSONResponse({"success": False, "message": "password 至少 6 位"}, status_code=400)

    payload = await _register_without_verification(username, password, email)
    if isinstance(payload, JSONResponse):
        return payload
    if isinstance(payload, dict) and payload.get("__proxy_error__"):
        status_code = int(payload.get("status_code") or 400)
        raw_error = payload.get("payload")
        if status_code == 409 or "存在" in _error_message(raw_error, status_code):
            payload = await _proxy_json(
                "POST", "/api/auth/login", json_body={"username": username, "password": password}
            )
        else:
            return JSONResponse(
                {
                    "success": False,
                    "message": _error_message(raw_error, status_code),
                    "data": raw_error,
                },
                status_code=status_code,
            )
    token = _token_from_auth_response(payload)
    if not token:
        return JSONResponse(
            {"success": False, "message": "账号创建成功但未返回 token", "data": payload},
            status_code=502,
        )
    overview = await _proxy_json(
        "GET", "/api/account/bootstrap", authorization=token, return_error_payload=True
    )
    return {
        "success": True,
        "data": {
            "market_base_url": _market_base_url(),
            "username": username,
            "email": email,
            "password": password,
            "token": token,
            "overview_ok": not (isinstance(overview, dict) and overview.get("__proxy_error__")),
            "overview": (
                overview.get("payload")
                if isinstance(overview, dict) and overview.get("__proxy_error__")
                else overview
            ),
        },
    }
