"""FastAPI 应用工厂：装配中间件、路由、静态资源与 SPA fallback。"""

from __future__ import annotations

import inspect
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Config, get_config
from app.infrastructure.mods.mod_auth import ModContextMiddleware
from app.middleware.auth_rate_limit import AuthRateLimitMiddleware
from app.middleware.csrf import CSRFMiddleware
from app.middleware.global_rate_limit import GlobalRateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.xss_sanitizer import XSSSanitizerMiddleware
from app.security import LanCidrGuard, LanLicenseGuard

from .cors import (
    lan_origin_regex_enabled,
    resolve_cors_allow_origin_regex,
    resolve_cors_allow_origins,
)
from .lifespan import lifespan
from .middleware_extra import register_extra_middleware, register_prometheus_metrics
from .static_mounts import mount_vue_dist_assets_dir, mount_vue_dist_public_static

logger = logging.getLogger(__name__)


def create_fastapi_app(
    config_object: type[Config] | None = None,
    enable_cors: bool = True,
    enable_docs: bool = True,
) -> FastAPI:
    if config_object is None:
        config_object = get_config("default")

    from app.mod_sdk.edition_policy import configure_edition_defaults

    configure_edition_defaults(
        desktop=getattr(config_object, "DESKTOP_MODE", False)
        or (os.environ.get("XCAGI_DESKTOP_MODE") or "").strip().lower()
        in {"1", "true", "yes", "on"}
    )

    from app.infrastructure.cache.wiring import wire_cache_port

    wire_cache_port()

    if not getattr(config_object, "SECRET_KEY", None):
        is_debug = getattr(config_object, "DEBUG", False)
        is_desktop = getattr(config_object, "DESKTOP_MODE", False)
        if not is_debug and not is_desktop:
            raise RuntimeError(
                "SECRET_KEY must be set in production. "
                "Set the SECRET_KEY environment variable or use DevelopmentConfig for local development."
            )

    app = FastAPI(
        title="XCAGI FastAPI",
        description="XCAGI 企业 AI 员工平台 - FastAPI 版本",
        version="8.0.0",
        docs_url="/docs" if enable_docs else None,
        redoc_url="/redoc" if enable_docs else None,
        lifespan=lifespan,
    )

    app.state.config = config_object

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(XSSSanitizerMiddleware)

    if enable_cors:
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
            lan_origin_regex_enabled()
            and "allow_private_network" in inspect.signature(CORSMiddleware).parameters
        ):
            _cors_kw["allow_private_network"] = True
        app.add_middleware(CORSMiddleware, **_cors_kw)

    app.add_middleware(ModContextMiddleware)
    app.add_middleware(LanLicenseGuard)
    app.add_middleware(LanCidrGuard)
    app.add_middleware(GlobalRateLimitMiddleware)
    app.add_middleware(AuthRateLimitMiddleware)

    logging.basicConfig(
        level=getattr(config_object, "LOG_LEVEL", "INFO"),
        format=getattr(
            config_object, "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ),
    )

    from app.fastapi_routes import register_all_routes

    register_all_routes(app)

    from app.middleware.error_handler import register_exception_handlers

    register_exception_handlers(app)

    try:
        from app.utils.metrics import init_metrics

        init_metrics("XCAGI", os.environ.get("XCAGI_VERSION", "9.0.0"))
    except Exception as e:
        logger.warning("Prometheus init_metrics skipped: %s", e)

    register_extra_middleware(app)
    register_prometheus_metrics(app)

    try:
        from app.fastapi_app.mod_startup import bootstrap_mod_extensions_sync

        bootstrap_mod_extensions_sync(app)
    except Exception as e:
        logger.warning("Mod extensions staged load failed (lifespan may retry): %s", e)

    mount_vue_dist_public_static(app)
    mount_vue_dist_assets_dir(app)

    try:
        from app.fastapi_routes.spa_fallback import register_spa_history_fallback

        register_spa_history_fallback(app)
        logger.info("Registered Vue history fallback (/{fallback:path}) as the last route")
    except Exception as e:
        logger.exception("Failed to register SPA history fallback: %s", e)
        raise

    return app


def get_fastapi_app() -> FastAPI:
    if not hasattr(get_fastapi_app, "_app"):
        get_fastapi_app._app = create_fastapi_app()
    return get_fastapi_app._app
