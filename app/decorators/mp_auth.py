# -*- coding: utf-8 -*-
"""
小程序认证装饰器
"""
import functools
import hashlib
import hmac
import json
import logging
import time
import uuid

from flask import current_app, g, request

from app.utils.mp_response import error

logger = logging.getLogger(__name__)


def verify_jwt_token(token: str) -> dict | None:
    """验证 JWT Token"""
    try:
        secret_key = current_app.config.get("SECRET_KEY", "default-secret-key")

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


def generate_jwt_token(user_id: int, openid: str, expires_hours: int = 720) -> str:
    """生成 JWT Token"""
    secret_key = current_app.config.get("SECRET_KEY", "default-secret-key")

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


def mp_auth_required(f):
    """小程序登录验证装饰器"""

    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return error("未授权", 401, {"error": "missing_token"})

        token = auth_header[7:].strip()
        payload = verify_jwt_token(token)

        if not payload:
            return error("token 无效或已过期", 401, {"error": "invalid_token"})

        g.current_user_id = payload.get("user_id")
        g.current_openid = payload.get("openid")

        return f(*args, **kwargs)

    return decorated_function


def get_current_mp_user_id() -> int | None:
    """获取当前小程序用户ID"""
    return getattr(g, "current_user_id", None)


def get_current_mp_openid() -> str | None:
    """获取当前用户 openid"""
    return getattr(g, "current_openid", None)
