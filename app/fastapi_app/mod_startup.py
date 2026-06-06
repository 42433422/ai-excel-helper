# -*- coding: utf-8 -*-
"""Mod 分阶段启动：先挂载主客户 Mod，其余在后台 load，缩短 HTTP 可监听时间。"""

from __future__ import annotations

import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)

_bg_started = False
_bg_lock = threading.Lock()


def _load_bundled_host_mods(mm: Any) -> list[str]:
    """同步加载当前 SKU 宿主 bridge 包（数量少、侧栏依赖）。"""
    loaded: list[str] = []
    try:
        from app.mod_sdk.product_skus import bundled_mod_ids_for_sku, resolve_product_sku

        sku = resolve_product_sku()
        if not sku:
            return loaded
        for mid in bundled_mod_ids_for_sku(sku):
            mid = str(mid or "").strip()
            if not mid or mid in mm._loaded_mods:
                continue
            try:
                if mm.load_mod(mid):
                    loaded.append(mid)
            except Exception:
                logger.debug("bundled mod load skipped: %s", mid, exc_info=True)
    except Exception:
        logger.debug("bundled mod ids resolve skipped", exc_info=True)
    return loaded


def schedule_background_mod_load(app: Any) -> None:
    """在后台线程执行 load_all_mods + 补挂路由，避免阻塞 create_fastapi_app。"""
    global _bg_started
    with _bg_lock:
        if _bg_started:
            return
        _bg_started = True

    def _work() -> None:
        try:
            from app.fastapi_app.startup_timing import mark_startup
            from app.infrastructure.mods.mod_manager import get_mod_manager, load_mod_routes

            mm = get_mod_manager()
            loaded = mm.load_all_mods()
            load_mod_routes(app, mm)
            app.state.mods_routes_loaded = True
            app.state.mods_full_load_done = True
            mark_startup("mod_background_done")
            logger.info(
                "[mod_startup] background load_all_mods done (%s ids)",
                len(loaded),
            )
        except Exception:
            logger.exception("[mod_startup] background load_all_mods failed")

    threading.Thread(
        target=_work,
        name="xcagi-mod-background-load",
        daemon=True,
    ).start()
    app.state.mods_background_load_scheduled = True


def bootstrap_mod_extensions_sync(app: Any) -> None:
    """
    同步阶段：主客户 Mod（太阳鸟等）+ 当前 SKU 宿主 bridge；完整扫描放后台。
    """
    from app.infrastructure.mods.mod_manager import (
        get_mod_manager,
        is_mods_disabled,
        load_mod_routes,
        mount_on_disk_primary_client_mods,
    )

    app.state.mods_routes_loaded = False
    app.state.mods_full_load_done = False
    app.state.mods_background_load_scheduled = False

    if is_mods_disabled():
        app.state.mods_routes_loaded = True
        app.state.mods_full_load_done = True
        return

    mm = get_mod_manager()
    client_ids = mount_on_disk_primary_client_mods(mm)
    bundled = _load_bundled_host_mods(mm)
    load_mod_routes(app, mm)
    app.state.mods_routes_loaded = True
    try:
        from app.fastapi_app.startup_timing import mark_startup

        mark_startup("mod_staged")
    except Exception:
        pass
    logger.info(
        "Mod extensions staged (client=%s, bundled=%s); scheduling background load",
        client_ids,
        len(bundled),
    )
    schedule_background_mod_load(app)


__all__ = ["bootstrap_mod_extensions_sync", "schedule_background_mod_load"]
