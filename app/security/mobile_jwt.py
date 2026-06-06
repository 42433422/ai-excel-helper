"""XCAGI Android 客户端 JWT（aud=xcagi-mobile，与小程序 JWT 区分）。"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)

MOBILE_JWT_AUD = "xcagi-mobile"
MOBILE_ACCESS_TTL_HOURS = 24
MOBILE_REFRESH_TTL_HOURS = 168


def _secret_key() -> str:
    return os.environ.get("SECRET_KEY", "xcagi-dev-secret")


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (4 - len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def verify_mobile_jwt(token: str) -> dict[str, Any] | None:
    try:
        secret = _secret_key().encode("utf-8")
        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload = json.loads(_b64url_decode(parts[1]).decode("utf-8"))
        signature = _b64url_decode(parts[2])
        message = f"{parts[0]}.{parts[1]}".encode()
        expected = hmac.new(secret, message, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            return None
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        if payload.get("aud") != MOBILE_JWT_AUD:
            return None
        return payload
    except Exception as exc:
        logger.debug("mobile jwt verify failed: %s", exc)
        return None


def issue_mobile_tokens(
    *,
    user_id: int,
    session_id: str,
    account_kind: str = "enterprise",
    username: str = "",
) -> dict[str, str]:
    access = _issue_token(
        user_id=user_id,
        session_id=session_id,
        account_kind=account_kind,
        username=username,
        ttl_hours=MOBILE_ACCESS_TTL_HOURS,
        token_type="access",
    )
    refresh = _issue_token(
        user_id=user_id,
        session_id=session_id,
        account_kind=account_kind,
        username=username,
        ttl_hours=MOBILE_REFRESH_TTL_HOURS,
        token_type="refresh",
    )
    return {"access_token": access, "refresh_token": refresh}


def refresh_mobile_access_token(refresh_token: str) -> dict[str, str] | None:
    payload = verify_mobile_jwt(refresh_token)
    if not payload or payload.get("typ") != "refresh":
        return None
    uid = payload.get("user_id")
    sid = payload.get("session_id")
    if uid is None or not sid:
        return None
    return issue_mobile_tokens(
        user_id=int(uid),
        session_id=str(sid),
        account_kind=str(payload.get("account_kind") or "enterprise"),
        username=str(payload.get("username") or ""),
    )


def _issue_token(
    *,
    user_id: int,
    session_id: str,
    account_kind: str,
    username: str,
    ttl_hours: int,
    token_type: str,
) -> str:
    secret = _secret_key().encode("utf-8")
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "aud": MOBILE_JWT_AUD,
        "typ": token_type,
        "user_id": user_id,
        "session_id": session_id,
        "account_kind": account_kind,
        "username": username,
        "iat": now,
        "exp": now + ttl_hours * 3600,
        "jti": uuid.uuid4().hex,
    }
    header_enc = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_enc = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    message = f"{header_enc}.{payload_enc}".encode()
    sig = hmac.new(secret, message, hashlib.sha256).digest()
    return f"{header_enc}.{payload_enc}.{_b64url_encode(sig)}"


def user_id_from_mobile_bearer(authorization: str | None) -> int | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    payload = verify_mobile_jwt(authorization[7:].strip())
    if not payload or payload.get("typ") != "access":
        return None
    uid = payload.get("user_id")
    return int(uid) if uid is not None else None
