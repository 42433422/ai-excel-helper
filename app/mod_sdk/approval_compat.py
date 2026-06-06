# -*- coding: utf-8 -*-
"""里程碑 E：审批 API 经 ``xcagi-approval-bridge`` 门面（handler 委托宿主 approval 路由）。"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

APPROVAL_BRIDGE_MOD_ID = "xcagi-approval-bridge"

logger = logging.getLogger(__name__)

HOST_PREFIX = "/api/approval"
FACADE_PREFIX = f"/api/mod/{APPROVAL_BRIDGE_MOD_ID}"


def _truthy_env(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _resolve_mod_dir() -> Path | None:
    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager

        meta = get_mod_manager().get_mod(APPROVAL_BRIDGE_MOD_ID)
        if meta and meta.mod_path and (Path(meta.mod_path) / "manifest.json").is_file():
            return Path(meta.mod_path)
    except Exception:
        pass
    trial = Path(__file__).resolve().parents[2] / "mods" / APPROVAL_BRIDGE_MOD_ID
    return trial if (trial / "manifest.json").is_file() else None


def _read_manifest() -> dict[str, Any]:
    mod_dir = _resolve_mod_dir()
    if not mod_dir:
        return {}
    try:
        data = json.loads((mod_dir / "manifest.json").read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def is_approval_mod_installed() -> bool:
    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager, is_mods_disabled

        if is_mods_disabled():
            return False
        for row in get_mod_manager().list_all_mods():
            if str(row.get("id") or "").strip() == APPROVAL_BRIDGE_MOD_ID:
                return True
    except Exception:
        pass
    return _resolve_mod_dir() is not None


def is_approval_via_mod_enabled() -> bool:
    if _truthy_env("XCAGI_DISABLE_APPROVAL_MOD"):
        return False
    if _truthy_env("XCAGI_APPROVAL_VIA_MOD"):
        return True
    if not is_approval_mod_installed():
        return False
    cfg = _read_manifest().get("config") or {}
    if isinstance(cfg, dict) and cfg.get("approval_facade") is True:
        return True
    return False


def list_approval_facade_registry() -> dict[str, Any]:
    via = is_approval_via_mod_enabled()
    endpoints = [
        "GET /requests",
        "GET /requests/{id}",
        "POST /requests",
        "POST /requests/{id}/approve",
        "POST /requests/{id}/reject",
        "POST /requests/{id}/withdraw",
        "DELETE /requests/{id}",
        "POST /requests/cleanup",
        "GET /flows",
        "POST /flows",
        "PUT /flows/{id}",
        "PATCH /flows/{id}/active",
        "DELETE /flows/{id}",
    ]
    return {
        "ok": True,
        "mod_id": APPROVAL_BRIDGE_MOD_ID,
        "host_prefix": HOST_PREFIX,
        "facade_prefix": FACADE_PREFIX,
        "endpoint_count": len(endpoints),
        "endpoints": endpoints,
        "execution_via_mod_facade": via,
        "execution_path": "mod_facade" if via else "host.api",
        "delegate": "app.fastapi_routes.approval",
        "note": "里程碑 E：审批 HTTP 入口在 Mod；ORM 与 DB 仍在宿主。",
    }


__all__ = [
    "APPROVAL_BRIDGE_MOD_ID",
    "FACADE_PREFIX",
    "HOST_PREFIX",
    "is_approval_mod_installed",
    "is_approval_via_mod_enabled",
    "list_approval_facade_registry",
]
