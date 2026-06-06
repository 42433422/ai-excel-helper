"""沙盒 FastAPI：白名单路由 + Mod 加载 + 静态资源 + SPA fallback。"""

from __future__ import annotations

import inspect
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_config
from app.di.registry import get_service_registry
from app.infrastructure.cache.wiring import wire_cache_port
from app.infrastructure.mods.mod_auth import ModContextMiddleware
from app.middleware.csrf import CSRFMiddleware
from app.middleware.error_handler import register_exception_handlers
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.xss_sanitizer import XSSSanitizerMiddleware
from app.security import LanCidrGuard, LanLicenseGuard

from sandbox_app.mock_routes import mount_api_fallback_last, mount_mock_routes
from sandbox_app.route_whitelist import mount_whitelist_routes
from sandbox_app.sandbox_settings import resolve_vue_dist_dir
from sandbox_app.spa_static import (
    mount_vue_static,
    register_root_index,
    register_sandbox_spa_fallback,
)

logger = logging.getLogger(__name__)


def _lan_origin_regex_enabled() -> bool:
    raw = (os.environ.get("XCAGI_DEV_ALLOW_LAN_CORS") or "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return os.environ.get("XCAGI_DEBUG", "1").strip() == "1"


def resolve_cors_allow_origins() -> list[str]:
    raw = (os.environ.get("CORS_ALLOW_ORIGINS") or "").strip()
    if raw:
        origins = [x.strip() for x in raw.split(",") if x.strip() and x.strip() != "*"]
        if origins:
            return origins
    return [
        "http://127.0.0.1:5099",
        "http://localhost:5099",
        "https://xiu-ci.com",
        "https://www.xiu-ci.com",
        "http://127.0.0.1:5001",
        "http://localhost:5001",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]


def resolve_cors_allow_origin_regex() -> str | None:
    explicit = (os.environ.get("CORS_ALLOW_ORIGIN_REGEX") or "").strip()
    if explicit:
        return explicit
    if _lan_origin_regex_enabled():
        return (
            r"^http://(192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
            r"|172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})(:\d+)?$"
        )
    return None


async def _init_mods_async(app: FastAPI) -> None:
    if getattr(app.state, "mods_routes_loaded", False):
        return
    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager, load_mod_routes

        mm = get_mod_manager()
        mm.load_all_mods()
        load_mod_routes(app, mm)
        app.state.mods_routes_loaded = True
        logger.info("sandbox: mod routes mounted in lifespan")
    except Exception as e:
        logger.warning("sandbox lifespan mod init failed: %s", e)


@asynccontextmanager
async def sandbox_lifespan(app: FastAPI):
    logger.info("sandbox lifespan: starting mod init")
    try:
        await _init_mods_async(app)
    except Exception as e:
        logger.warning("sandbox lifespan mod init: %s", e)
    yield
    logger.info("sandbox lifespan: shutdown")


def create_sandbox_app() -> FastAPI:
    config_object = get_config("development")

    wire_cache_port()

    app = FastAPI(
        title="XCAGI Mod Sandbox",
        description="轻量 Mod 在线测试环境（复用仓库 app.*）",
        version="0.1.0",
        lifespan=sandbox_lifespan,
    )
    app.state.config = config_object
    app.state.services = get_service_registry()

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(XSSSanitizerMiddleware)

    _cors_regex = resolve_cors_allow_origin_regex()
    _cors_kw: dict = dict(
        allow_origins=resolve_cors_allow_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    if _cors_regex:
        _cors_kw["allow_origin_regex"] = _cors_regex
    if (
        _lan_origin_regex_enabled()
        and "allow_private_network" in inspect.signature(CORSMiddleware).parameters
    ):
        _cors_kw["allow_private_network"] = True
    app.add_middleware(CORSMiddleware, **_cors_kw)

    app.add_middleware(ModContextMiddleware)
    app.add_middleware(LanLicenseGuard)
    app.add_middleware(LanCidrGuard)

    mount_whitelist_routes(app)
    _mount_minimal_mod_store_if_needed(app)
    mount_mock_routes(app)

    register_exception_handlers(app)
    _register_sandbox_http_middleware(app)

    app.state.mods_routes_loaded = False
    try:
        from app.infrastructure.mods.mod_manager import (
            get_mod_manager,
            is_mods_disabled,
            load_mod_routes,
        )

        if not is_mods_disabled():
            mm = get_mod_manager()
            mm.load_all_mods()
            load_mod_routes(app, mm)
            app.state.mods_routes_loaded = True
            logger.info("sandbox: mod routes mounted before API fallback")
    except Exception as e:
        logger.warning("sandbox: mod sync load failed (lifespan may retry): %s", e)

    mount_api_fallback_last(app)

    vue_dir = resolve_vue_dist_dir()
    mount_vue_static(app, vue_dir)
    register_root_index(app, vue_dir)
    register_sandbox_spa_fallback(app, vue_dir)

    return app


def _mount_minimal_mod_store_if_needed(app: FastAPI) -> None:
    exists = any(
        getattr(route, "path", "") == "/api/mod-store/install"
        for route in getattr(app, "routes", [])
    )
    if exists:
        return
    try:
        from sandbox_app.minimal_mod_store_routes import router as minimal_mod_store_router

        app.include_router(minimal_mod_store_router)
        logger.info("sandbox: mounted minimal /api/mod-store/install fallback")
    except Exception as e:
        logger.warning("sandbox: minimal mod-store fallback unavailable: %s", e)


def _register_sandbox_http_middleware(app: FastAPI) -> None:
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
        logger.info("sandbox %s %s", request.method, request.url.path)
        from app.request_active_mod_ctx import (
            parse_active_mod_header,
            reset_request_active_mod_id,
            set_request_active_mod_id,
        )

        active_mod = parse_active_mod_header(request.headers)
        am_token = set_request_active_mod_id(active_mod)
        try:
            return await call_next(request)
        finally:
            reset_request_active_mod_id(am_token)
