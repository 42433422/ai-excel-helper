# -*- coding: utf-8 -*-
"""桌面/发行版启动时确保 Mod 种子与加载（可交付首启）。"""

from __future__ import annotations

import asyncio
import logging
import os

from fastapi import FastAPI

logger = logging.getLogger(__name__)


async def ensure_deliverable_runtime(app: FastAPI) -> None:
    """首启：复制内置 mods → load_all → 可选自动 bootstrap（默认仅种子，不阻塞公网）。"""
    from app.desktop_runtime.paths import is_desktop_mode
    from app.mod_sdk.deliverable_status import build_deliverable_status
    from app.mod_sdk.edition_policy import (
        resolve_edition,
        seed_edition_mods_from_bundle,
    )

    if not is_desktop_mode() and resolve_edition() == "full":
        return

    edition = resolve_edition()
    if edition == "full":
        return

    try:
        seeded = await asyncio.to_thread(seed_edition_mods_from_bundle, edition)
        if seeded:
            logger.info("Deliverable seed: %s", seeded)
    except Exception as exc:
        logger.warning("Deliverable mod seed failed: %s", exc)

    if getattr(app.state, "mods_full_load_done", False):
        logger.info("Deliverable mod load skipped (mods_full_load_done)")
    elif getattr(app.state, "mods_background_load_scheduled", False):
        logger.info("Deliverable mod load skipped (background load in progress)")
    else:
        try:
            from app.infrastructure.mods.mod_manager import get_mod_manager, load_mod_routes

            mm = get_mod_manager()
            await asyncio.to_thread(mm.load_all_mods)
            if not getattr(app.state, "mods_routes_loaded", False):
                load_mod_routes(app, mm)
                app.state.mods_routes_loaded = True
            app.state.mods_full_load_done = True
        except Exception as exc:
            logger.warning("Deliverable mod load failed: %s", exc)
            return

    status = build_deliverable_status()
    app.state.deliverable_status = status

    if status.get("deliverable"):
        logger.info("Deliverable runtime ready (edition=%s)", edition)
        return

    auto = (os.environ.get("XCAGI_AUTO_BOOTSTRAP_EDITION") or "0").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    if not auto:
        logger.info(
            "Deliverable not ready (edition=%s); set XCAGI_AUTO_BOOTSTRAP_EDITION=1 to fetch from catalog",
            edition,
        )
        return

    try:
        from app.mod_sdk.edition_bootstrap import bootstrap_edition_pack

        result = await bootstrap_edition_pack(edition)  # type: ignore[arg-type]
        app.state.deliverable_bootstrap = result
        logger.info("Auto bootstrap edition pack: ready=%s", result.get("ready"))
    except Exception as exc:
        logger.warning("Auto bootstrap edition pack failed: %s", exc)


__all__ = ["ensure_deliverable_runtime"]
