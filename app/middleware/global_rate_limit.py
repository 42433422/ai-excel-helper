# -*- coding: utf-8 -*-
"""全站 API 速率限制（按 IP + 路径前缀）。"""

from __future__ import annotations

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.utils.rate_limiter import check_rate_limit


def _global_rate_limit_enabled() -> bool:
    return (os.environ.get("XCAGI_GLOBAL_RATE_LIMIT") or "1").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _max_requests() -> int:
    try:
        return int(os.environ.get("XCAGI_GLOBAL_RATE_LIMIT_MAX", "300"))
    except ValueError:
        return 300


def _window_seconds() -> int:
    try:
        return int(os.environ.get("XCAGI_GLOBAL_RATE_LIMIT_WINDOW", "60"))
    except ValueError:
        return 60


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    """对 /api/* 请求做粗粒度限流，health/metrics/docs 除外。"""

    async def dispatch(self, request: Request, call_next):
        if not _global_rate_limit_enabled():
            return await call_next(request)

        path = request.url.path or ""
        if not path.startswith("/api/"):
            return await call_next(request)
        if path.startswith(("/api/health", "/api/system/health", "/metrics")):
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        endpoint = f"global:{path.split('/')[2] if path.count('/') >= 2 else 'api'}"
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
                    "message": "请求过于频繁，请稍后再试",
                    "retry_after": result.get("retry_after", 60),
                },
            )
        response = await call_next(request)
        if "X-RateLimit-Remaining" not in response.headers:
            remaining = result.get("remaining")
            if remaining is not None:
                response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
