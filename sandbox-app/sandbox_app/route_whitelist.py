"""仅注册 Mod 沙盒需要的 FHD 路由（其余业务由 mock_routes 桩掉）。"""

from __future__ import annotations

import logging

from fastapi import FastAPI

logger = logging.getLogger(__name__)


def mount_whitelist_routes(app: FastAPI) -> None:
    """按顺序挂载；失败的路由记录警告并跳过。"""

    _safe_include(app, _mods_router, "mods")
    _safe_include(app, _mod_store_router, "mod-store", prefix="/api/mod-store")
    _safe_include(app, _legacy_auth_router, "legacy-auth")
    _safe_include(app, _system_router, "system")
    _safe_include(app, _state_router, "state")
    _safe_include(app, _legacy_conversation_router, "legacy-conversation")


def _safe_include(app, loader, name: str, prefix: str | None = None) -> None:
    try:
        router = loader()
        if router is None:
            logger.warning("sandbox whitelist: %s returned None", name)
            return
        if prefix:
            app.include_router(router, prefix=prefix)
        else:
            app.include_router(router)
        logger.info("sandbox whitelist: mounted %s", name)
    except Exception as e:
        logger.warning("sandbox whitelist: skip %s: %s", name, e)


def _mods_router():
    from app.fastapi_routes.mods_routes import get_mods_router

    return get_mods_router()


def _mod_store_router():
    from app.fastapi_routes.mod_store_routes import router as mod_store_router

    return mod_store_router


def _legacy_auth_router():
    from app.fastapi_routes.legacy_auth import router as legacy_auth_router

    return legacy_auth_router


def _system_router():
    from app.fastapi_routes.system_routes import router as system_router

    return system_router


def _state_router():
    from app.fastapi_routes.state import router as state_router

    return state_router


def _legacy_conversation_router():
    from app.fastapi_routes.legacy_conversation import router as legacy_conversation_router

    return legacy_conversation_router
