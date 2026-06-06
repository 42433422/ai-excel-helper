"""
小程序认证装饰器（JWT 密钥来自 Config；请求取自 ASGI ContextVar）。
"""

from __future__ import annotations

import functools
import hashlib
import hmac
import json
import logging
import time
import uuid
from contextvars import ContextVar, Token

from app.config import Config
from app.utils.mp_response import error

logger = logging.getLogger(__name__)

_mp_user_id_ctx: ContextVar[int | None] = ContextVar("mp_user_id", default=None)
_mp_openid_ctx: ContextVar[str | None] = ContextVar("mp_openid", default=None)


def _jwt_secret() -> str:
    raw = getattr(Config, "SECRET_KEY", None) or ""
    return str(raw)


def verify_jwt_token(token: str) -> dict | None:
    """验证 JWT Token"""
    try:
        secret_key = _jwt_secret()

        parts = token.split(".")
        if len(parts) != 3:
            return None

        def base64url_decode(data: str) -> bytes:
            import base64

            padding = "=" * (4 - len(data) % 4)
            return base64.urlsafe_b64decode(data + padding)

        header = json.loads(base64url_decode(parts[0]))
        payload = json.loads(base64url_decode(parts[1]))
        signature = base64url_decode(parts[2])

        message = f"{parts[0]}.{parts[1]}"
        expected_signature = hmac.new(
            secret_key.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).digest()

        if not hmac.compare_digest(signature, expected_signature):
            return None

        if payload.get("exp", 0) < int(time.time()):
            return None

        return payload
    except Exception as e:
        logger.error(f"Token 验证失败: {e}")
        return None


def generate_jwt_token(user_id: int, openid: str, expires_hours: int = 4) -> str:
    """生成 JWT Token"""
    secret_key = _jwt_secret()

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "user_id": user_id,
        "openid": openid,
        "iat": int(time.time()),
        "exp": int(time.time()) + (expires_hours * 3600),
        "jti": uuid.uuid4().hex,
    }

    def base64url_encode(data: bytes) -> str:
        import base64

        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

    header_encoded = base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_encoded = base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    message = f"{header_encoded}.{payload_encoded}"
    signature = hmac.new(
        secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    signature_encoded = base64url_encode(signature)

    return f"{header_encoded}.{payload_encoded}.{signature_encoded}"


def generate_refresh_token(user_id: int, openid: str) -> str:
    """生成 Refresh Token（7 天有效，仅用于换取新 access token）。"""
    return generate_jwt_token(user_id, openid, expires_hours=168)


def refresh_access_token(refresh_token_str: str) -> tuple[str, str] | None:
    """用 refresh token 换取新的 access + refresh token 对。"""
    payload = verify_jwt_token(refresh_token_str)
    if payload is None:
        return None
    user_id = payload.get("user_id")
    openid = payload.get("openid", "")
    if user_id is None:
        return None
    new_access = generate_jwt_token(int(user_id), str(openid), expires_hours=4)
    new_refresh = generate_refresh_token(int(user_id), str(openid))
    return new_access, new_refresh


def mp_auth_required(f):
    """小程序登录验证装饰器"""

    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        from app.http.request_context import get_current_http_request

        req = get_current_http_request()
        if req is None:
            return error("未授权", 401, {"message": "no_request_context"})

        auth_header = req.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return error("未授权", 401, {"message": "missing_token"})

        token = auth_header[7:].strip()
        payload = verify_jwt_token(token)

        if not payload:
            return error("token 无效或已过期", 401, {"message": "invalid_token"})

        t_uid: Token[int | None] = _mp_user_id_ctx.set(int(payload.get("user_id")))
        t_oid: Token[str | None] = _mp_openid_ctx.set(str(payload.get("openid") or ""))
        try:
            return f(*args, **kwargs)
        finally:
            _mp_user_id_ctx.reset(t_uid)
            _mp_openid_ctx.reset(t_oid)

    return decorated_function


def get_current_mp_user_id() -> int | None:
    """获取当前小程序用户ID"""
    return _mp_user_id_ctx.get()


def get_current_mp_openid() -> str | None:
    """获取当前用户 openid"""
    return _mp_openid_ctx.get()
