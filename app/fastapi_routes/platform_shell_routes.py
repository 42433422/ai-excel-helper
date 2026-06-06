# -*- coding: utf-8 -*-
"""GET /api/platform-shell/capabilities — 通用化宿主能力清单（阶段 4）。"""

from __future__ import annotations

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/platform-shell", tags=["platform-shell"])


@router.get("/capabilities")
async def platform_shell_capabilities():
    installed: list[str] = []
    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager

        for m in get_mod_manager().list_all_mods():
            mid = str(m.get("id") or "").strip()
            if mid:
                installed.append(mid)
    except Exception as exc:
        logger.warning("platform_shell: list mods failed: %s", exc)

    from app.mod_sdk.platform_shell import build_platform_shell_payload

    return {"success": True, "data": build_platform_shell_payload(installed)}


@router.get("/decoupling-progress")
async def decoupling_progress():
    installed: list[str] = []
    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager

        for m in get_mod_manager().list_all_mods():
            mid = str(m.get("id") or "").strip()
            if mid:
                installed.append(mid)
    except Exception as exc:
        logger.warning("decoupling-progress: list mods failed: %s", exc)

    from app.mod_sdk.decoupling_progress import build_decoupling_progress_payload

    return {"success": True, "data": build_decoupling_progress_payload(installed)}


@router.get("/deliverable-status")
async def platform_shell_deliverable_status():
    """可交付验收：edition 包是否装齐、Mod 路由是否挂载、建议下一步操作。"""
    from app.mod_sdk.deliverable_status import build_deliverable_status

    return {"success": True, "data": build_deliverable_status()}
