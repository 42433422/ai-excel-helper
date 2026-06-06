# -*- coding: utf-8 -*-
"""认证相关 API 专用速率限制（防暴力破解）。"""

from __future__ import annotations

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.utils.rate_limiter import check_rate_limit

_AUTH_PREFIXES = (
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/forgot-password",
    "/api/auth/reset-password",
    "/api/mobile/v1/auth/login",
)


def _auth_rate_limit_enabled() -> bool:
    return (os.environ.get("XCAGI_AUTH_RATE_LIMIT") or "1").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _max_requests() -> int:
    try:
        return int(os.environ.get("XCAGI_AUTH_RATE_LIMIT_MAX", "10"))
    except ValueError:
        return 10


def _window_seconds() -> int:
    try:
        return int(os.environ.get("XCAGI_AUTH_RATE_LIMIT_WINDOW", "60"))
    except ValueError:
        return 60


def _is_auth_path(path: str) -> bool:
    if not path.startswith("/api/"):
        return False
    for prefix in _AUTH_PREFIXES:
        if path == prefix or path.startswith(prefix + "/"):
            return True
    return False


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    """对登录/注册/找回密码等路径按 IP 限流（默认 10 次/分钟）。"""

    async def dispatch(self, request: Request, call_next):
        if not _auth_rate_limit_enabled():
            return await call_next(request)

        path = request.url.path or ""
        if not _is_auth_path(path):
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        endpoint = f"auth:{path.rstrip('/')}"
        key = f"{client}:{endpoint}"

        result = check_rate_limit(
            key,
            endpoint,
            max_requests=_max_requests(),
            window_seconds=_window_seconds(),
        )
        if not result.get("allowed", True):
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "code": "RATE_LIMITED",
                    "message": "认证请求过于频繁，请稍后再试",
                    "retry_after": result.get("retry_after", 60),
                },
            )
        return await call_next(request)
