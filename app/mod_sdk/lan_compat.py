# -*- coding: utf-8 -*-
"""里程碑 J：LAN 授权 API 经 ``xcagi-lan-license-bridge`` 门面。"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

LAN_BRIDGE_MOD_ID = "xcagi-lan-license-bridge"

logger = logging.getLogger(__name__)

HOST_PREFIX = "/api/lan"
FACADE_PREFIX = f"/api/mod/{LAN_BRIDGE_MOD_ID}/lan"


def _truthy_env(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _resolve_mod_dir() -> Path | None:
    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager

        meta = get_mod_manager().get_mod(LAN_BRIDGE_MOD_ID)
        if meta and meta.mod_path and (Path(meta.mod_path) / "manifest.json").is_file():
            return Path(meta.mod_path)
    except Exception:
        pass
    trial = Path(__file__).resolve().parents[2] / "mods" / LAN_BRIDGE_MOD_ID
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


def is_lan_mod_installed() -> bool:
    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager, is_mods_disabled

        if is_mods_disabled():
            return False
        for row in get_mod_manager().list_all_mods():
            if str(row.get("id") or "").strip() == LAN_BRIDGE_MOD_ID:
                return True
    except Exception:
        pass
    return _resolve_mod_dir() is not None


def is_lan_via_mod_enabled() -> bool:
    if _truthy_env("XCAGI_DISABLE_LAN_MOD"):
        return False
    if _truthy_env("XCAGI_LAN_VIA_MOD"):
        return True
    if not is_lan_mod_installed():
        return False
    cfg = _read_manifest().get("config") or {}
    if isinstance(cfg, dict) and cfg.get("lan_facade") is True:
        return True
    return False


def list_lan_facade_registry() -> dict[str, Any]:
    via = is_lan_via_mod_enabled()
    endpoints = [
        "GET /lan/host-info",
        "GET /lan/status",
        "GET /lan/access-requests/mine",
        "POST /lan/access-requests",
        "POST /lan/activate",
        "POST /lan/logout",
        "GET /lan/admin/whoami",
        "GET /lan/admin/keys",
        "POST /lan/admin/keys",
        "DELETE /lan/admin/keys/{id}",
        "GET /lan/admin/sessions",
        "DELETE /lan/admin/sessions/{jti}",
        "GET /lan/admin/audit",
        "GET /lan/admin/access-requests",
        "POST /lan/admin/access-requests/{id}/approve",
        "POST /lan/admin/access-requests/{id}/reject",
        "GET /lan/admin/allowlist",
        "DELETE /lan/admin/allowlist/{id}",
        "GET /lan/admin/settings",
        "POST /lan/admin/settings",
    ]
    return {
        "ok": True,
        "mod_id": LAN_BRIDGE_MOD_ID,
        "host_prefix": HOST_PREFIX,
        "facade_prefix": FACADE_PREFIX,
        "endpoint_count": len(endpoints),
        "endpoints": endpoints,
        "execution_via_mod_facade": via,
        "execution_path": "mod_facade" if via else "host.api",
        "delegate": "app.fastapi_routes.lan_*",
        "phase": "J",
        "note": "里程碑 J：LAN HTTP 入口在 Mod；LicenseGuard 与 DB 仍在宿主。",
    }


__all__ = [
    "FACADE_PREFIX",
    "HOST_PREFIX",
    "LAN_BRIDGE_MOD_ID",
    "is_lan_mod_installed",
    "is_lan_via_mod_enabled",
    "list_lan_facade_registry",
]
