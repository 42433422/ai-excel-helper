"""
基于 stdlib HMAC-SHA256 的紧凑 token 签发与校验。

格式：``<payload_b64>.<sig_b64>``

- ``payload`` = JSON({"jti": ..., "kid": ..., "iat": ..., "exp": ...})
- ``sig``     = HMAC_SHA256(secret, payload_b64).digest()

不引入 itsdangerous / PyJWT，零新依赖；签名比较使用 ``hmac.compare_digest``
保证常量时间，避免时序攻击。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass

from app.security.lan_config import LAN_LICENSE_SECRET_MIN_LENGTH


def _b64u_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64u_decode(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


@dataclass(frozen=True)
class TokenPayload:
    jti: str
    kid: str
    iat: int
    exp: int

    def is_expired(self, now: int | None = None) -> bool:
        ts = int(now if now is not None else time.time())
        return ts >= self.exp


class TokenError(ValueError):
    """token 解析或校验失败。"""


def issue_token(secret: str, kid: str, ttl_seconds: int) -> tuple[str, TokenPayload]:
    """
    返回 ``(token, payload)``；调用方应把 ``jti`` 写入会话表，
    便于服务端主动吊销或踢出。
    """
    if not secret or len(secret) < LAN_LICENSE_SECRET_MIN_LENGTH:
        raise TokenError(
            f"LAN_LICENSE_SECRET 未配置或长度不足（≥{LAN_LICENSE_SECRET_MIN_LENGTH} 字符）"
        )
    if ttl_seconds <= 0:
        raise TokenError("ttl_seconds must be positive")
    now = int(time.time())
    payload = TokenPayload(
        jti=secrets.token_urlsafe(18),
        kid=str(kid or ""),
        iat=now,
        exp=now + int(ttl_seconds),
    )
    body = json.dumps(
        {"jti": payload.jti, "kid": payload.kid, "iat": payload.iat, "exp": payload.exp},
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    body_b64 = _b64u_encode(body)
    sig = hmac.new(secret.encode("utf-8"), body_b64.encode("ascii"), hashlib.sha256).digest()
    token = f"{body_b64}.{_b64u_encode(sig)}"
    return token, payload


def parse_token(secret: str, token: str) -> TokenPayload:
    if not token or "." not in token:
        raise TokenError("invalid token format")
    if not secret:
        raise TokenError("server license secret missing")
    body_b64, sig_b64 = token.rsplit(".", 1)
    expected = hmac.new(secret.encode("utf-8"), body_b64.encode("ascii"), hashlib.sha256).digest()
    try:
        provided = _b64u_decode(sig_b64)
    except Exception as exc:
        raise TokenError("invalid signature encoding") from exc
    if not hmac.compare_digest(expected, provided):
        raise TokenError("signature mismatch")
    try:
        body = json.loads(_b64u_decode(body_b64))
    except Exception as exc:
        raise TokenError("invalid payload encoding") from exc
    try:
        return TokenPayload(
            jti=str(body["jti"]),
            kid=str(body.get("kid") or ""),
            iat=int(body["iat"]),
            exp=int(body["exp"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise TokenError("invalid payload schema") from exc


def hash_secret(text: str) -> str:
    """统一的一级密钥摘要算法（仅落库使用，非密码学口令哈希）。"""
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()
