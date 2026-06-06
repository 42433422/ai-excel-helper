# -*- coding: utf-8 -*-
"""里程碑 M：NeuroBus 诊断 API 经 ``xcagi-neuro-bus-bridge`` 门面。"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

NEURO_BUS_BRIDGE_MOD_ID = "xcagi-neuro-bus-bridge"

logger = logging.getLogger(__name__)

HOST_PREFIXES = ["/api/neurobus", "/api/neuro"]
FACADE_PREFIX = f"/api/mod/{NEURO_BUS_BRIDGE_MOD_ID}"


def _truthy_env(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _resolve_mod_dir() -> Path | None:
    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager

        meta = get_mod_manager().get_mod(NEURO_BUS_BRIDGE_MOD_ID)
        if meta and meta.mod_path and (Path(meta.mod_path) / "manifest.json").is_file():
            return Path(meta.mod_path)
    except Exception:
        pass
    trial = Path(__file__).resolve().parents[2] / "mods" / NEURO_BUS_BRIDGE_MOD_ID
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


def is_neuro_bus_mod_installed() -> bool:
    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager, is_mods_disabled

        if is_mods_disabled():
            return False
        for row in get_mod_manager().list_all_mods():
            if str(row.get("id") or "").strip() == NEURO_BUS_BRIDGE_MOD_ID:
                return True
    except Exception:
        pass
    return _resolve_mod_dir() is not None


def is_neuro_bus_via_mod_enabled() -> bool:
    if _truthy_env("XCAGI_DISABLE_NEURO_BUS_MOD"):
        return False
    if _truthy_env("XCAGI_NEURO_BUS_VIA_MOD"):
        return True
    if not is_neuro_bus_mod_installed():
        return False
    cfg = _read_manifest().get("config") or {}
    if isinstance(cfg, dict) and cfg.get("neuro_bus_facade") is True:
        return True
    return False


def list_neuro_bus_facade_registry() -> dict[str, Any]:
    via = is_neuro_bus_via_mod_enabled()
    mod_dir = _resolve_mod_dir()
    domains: list[str] = []
    if mod_dir:
        try:
            manifest = json.loads((mod_dir / "manifest.json").read_text(encoding="utf-8"))
            raw = (manifest.get("config") or {}).get("domains") or []
            if isinstance(raw, list):
                domains = [str(x) for x in raw if str(x).strip()]
        except Exception:
            pass
    endpoints = [
        "GET /neurobus/health",
        "GET /neurobus/stats",
        "GET /registry",
        "GET /handlers/registry",
        "GET /handlers/catalog",
        "POST /events/publish",
    ]
    handlers_via_mod = False
    handler_registry: dict[str, Any] = {}
    try:
        from app.mod_sdk.neuro_bus_handler_registry import (
            is_neuro_bus_handlers_via_mod_enabled,
            list_neuro_bus_handler_registry,
        )

        handlers_via_mod = is_neuro_bus_handlers_via_mod_enabled()
        handler_registry = list_neuro_bus_handler_registry()
    except Exception:
        pass
    return {
        "ok": True,
        "mod_id": NEURO_BUS_BRIDGE_MOD_ID,
        "host_prefixes": list(HOST_PREFIXES),
        "facade_prefix": FACADE_PREFIX,
        "endpoint_count": len(endpoints),
        "endpoints": endpoints,
        "domains": domains,
        "execution_via_mod_facade": via,
        "execution_path": "mod_bus_runtime" if via else "host.neuro_bus",
        "runtime_via_mod": via,
        "handlers_via_mod": handlers_via_mod,
        "handler_registry": handler_registry,
        "delegate": "mod.bus_runtime_factory (S)",
        "handler_delegate": "host.neuro_bus.domains.*_domain_handlers",
        "phase": "S" if via else ("N" if handlers_via_mod else "M+"),
        "note": "S：lifespan/publish 经 Mod 运行时 bundle；实现仍委托宿主 neuro_bus。",
    }


__all__ = [
    "FACADE_PREFIX",
    "HOST_PREFIXES",
    "NEURO_BUS_BRIDGE_MOD_ID",
    "is_neuro_bus_mod_installed",
    "is_neuro_bus_via_mod_enabled",
    "list_neuro_bus_facade_registry",
]
