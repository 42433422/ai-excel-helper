"""
HTTP 层 Neuro 读写 trace：采样、无 body 默认、不记敏感头。
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from starlette.requests import Request

logger = logging.getLogger(__name__)


def _redact_headers(headers: Any) -> dict[str, str]:
    out: dict[str, str] = {}
    skip = frozenset(
        {
            "authorization",
            "cookie",
            "set-cookie",
            "x-api-key",
            "x-auth-token",
        }
    )
    try:
        for k, v in headers.items():
            lk = str(k).lower()
            if lk in skip:
                out[str(k)] = "<redacted>"
            else:
                out[str(k)] = str(v)[:200]
    except Exception:
        pass
    return out


async def neuro_http_trace_middleware(request: Request, call_next):
    """作为 FastAPI ``@app.middleware(\"http\")`` 的最后一道（最外层）注册。"""
    try:
        from app.neuro_bus.application_neuro_bridge import publish_neuro_event
        from app.neuro_bus.integrations.intent_integration import is_neuro_stack_enabled
        from app.neuro_bus.neuro_trace_config import should_sample_http

        if not is_neuro_stack_enabled() or not should_sample_http():
            return await call_next(request)
    except Exception:
        return await call_next(request)

    rid = str(uuid.uuid4())
    t0 = time.perf_counter()
    path = request.url.path
    query = str(request.url.query)[:500]

    try:
        from app.neuro_bus.application_neuro_bridge import publish_neuro_event

        publish_neuro_event(
            "http.request.started",
            {
                "request_id": rid,
                "method": request.method,
                "path": path[:800],
                "query": query,
                "client": request.client.host if request.client else "",
                "headers": _redact_headers(request.headers),
            },
            domain="global",
        )
    except Exception:
        logger.debug("neuro http started skipped", exc_info=True)

    try:
        response = await call_next(request)
        ms = (time.perf_counter() - t0) * 1000.0
        try:
            from app.neuro_bus.application_neuro_bridge import publish_neuro_event

            publish_neuro_event(
                "http.request.completed",
                {
                    "request_id": rid,
                    "method": request.method,
                    "path": path[:800],
                    "status_code": response.status_code,
                    "latency_ms": round(ms, 3),
                },
                domain="global",
            )
        except Exception:
            logger.debug("neuro http completed skipped", exc_info=True)
        return response
    except Exception as exc:
        ms = (time.perf_counter() - t0) * 1000.0
        try:
            from app.neuro_bus.application_neuro_bridge import publish_neuro_event

            publish_neuro_event(
                "http.request.failed",
                {
                    "request_id": rid,
                    "method": request.method,
                    "path": path[:800],
                    "latency_ms": round(ms, 3),
                    "error": str(exc)[:300],
                },
                domain="global",
            )
        except Exception:
            logger.debug("neuro http failed skipped", exc_info=True)
        raise
