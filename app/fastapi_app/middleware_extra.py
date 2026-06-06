"""请求上下文、访问日志、Neuro HTTP trace、Prometheus /metrics、HTTP SLI。"""

from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request

from app.request_active_mod_ctx import (
    parse_active_mod_header,
    reset_request_active_mod_id,
    set_request_active_mod_id,
)

logger = logging.getLogger(__name__)


def register_http_sli_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def prometheus_http_sli(request: Request, call_next):
        path = request.url.path or ""
        if path == "/metrics":
            return await call_next(request)
        started = time.perf_counter()
        response = await call_next(request)
        try:
            from app.utils.metrics import record_http_request

            record_http_request(
                request.method, path, response.status_code, time.perf_counter() - started
            )
        except Exception:
            pass
        return response


def register_extra_middleware(app: FastAPI) -> None:
    """注册应用级 HTTP 中间件（内层：上下文与访问日志）。"""
    register_http_sli_middleware(app)

    @app.middleware("http")
    async def http_request_context(request: Request, call_next):
        from app.http.request_context import reset_current_http_request, set_current_http_request

        token = set_current_http_request(request)
        try:
            return await call_next(request)
        finally:
            reset_current_http_request(token)

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        import os

        verbose = (os.environ.get("XCAGI_REQUEST_LOG") or "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        path = request.url.path or ""
        if verbose or (
            logger.isEnabledFor(logging.DEBUG)
            and not path.startswith("/assets/")
            and path != "/api/health"
        ):
            logger.log(
                logging.INFO if verbose else logging.DEBUG,
                "FastAPI Request: %s %s",
                request.method,
                request.url,
            )
        active_mod = parse_active_mod_header(request.headers)
        am_token = set_request_active_mod_id(active_mod)
        try:
            response = await call_next(request)
            if verbose or (
                logger.isEnabledFor(logging.DEBUG)
                and not path.startswith("/assets/")
                and path != "/api/health"
            ):
                logger.log(
                    logging.INFO if verbose else logging.DEBUG,
                    "FastAPI Response: %s",
                    response.status_code,
                )
            return response
        finally:
            reset_request_active_mod_id(am_token)

    @app.middleware("http")
    async def neuro_http_trace_outer(request: Request, call_next):
        from app.middleware.neuro_http_trace import neuro_http_trace_middleware

        return await neuro_http_trace_middleware(request, call_next)


def register_prometheus_metrics(app: FastAPI) -> None:
    """注册 Prometheus 监控端点"""
    try:
        from fastapi.responses import Response
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

        @app.get("/metrics")
        async def metrics_endpoint():
            return Response(
                content=generate_latest(),
                media_type=CONTENT_TYPE_LATEST,
            )

        logger.info("✅ Prometheus 监控端点已注册 (/metrics)")
    except ImportError:
        logger.warning("⚠️ prometheus_client 未安装，监控端点不可用")
    except Exception as e:
        logger.warning("⚠️ Prometheus 监控端点注册失败：%s", e)
