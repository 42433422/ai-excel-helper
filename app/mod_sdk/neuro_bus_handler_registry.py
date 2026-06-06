# -*- coding: utf-8 -*-
"""里程碑 N：NeuroBus 领域处理器注册经 ``xcagi-neuro-bus-bridge`` 编排（实现仍在宿主）。"""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.mod_sdk.neuro_bus_compat import NEURO_BUS_BRIDGE_MOD_ID, _resolve_mod_dir

logger = logging.getLogger(__name__)


def _truthy_env(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _read_manifest() -> dict[str, Any]:
    mod_dir = _resolve_mod_dir()
    if not mod_dir:
        return {}
    try:
        data = json.loads((mod_dir / "manifest.json").read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def is_neuro_bus_handlers_via_mod_enabled() -> bool:
    if _truthy_env("XCAGI_DISABLE_NEURO_BUS_HANDLERS_MOD"):
        return False
    if _truthy_env("XCAGI_NEURO_BUS_HANDLERS_VIA_MOD"):
        return True
    cfg = _read_manifest().get("config") or {}
    if isinstance(cfg, dict) and cfg.get("neuro_bus_handlers_via_mod") is True:
        from app.mod_sdk.neuro_bus_compat import is_neuro_bus_mod_installed

        return is_neuro_bus_mod_installed()
    return False


@lru_cache(maxsize=4)
def _load_handler_providers_module(mod_path: str, mod_id: str):
    from app.infrastructure.mods.mod_manager import import_mod_backend_py

    return import_mod_backend_py(mod_path, mod_id, "handler_providers")


def _resolve_mod_path() -> tuple[str, str] | tuple[None, None]:
    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager

        meta = get_mod_manager().get_mod(NEURO_BUS_BRIDGE_MOD_ID)
        if meta and meta.mod_path:
            return NEURO_BUS_BRIDGE_MOD_ID, str(meta.mod_path)
    except Exception:
        logger.debug("neuro handler mod path via manager failed", exc_info=True)
    mod_dir = _resolve_mod_dir()
    if mod_dir:
        return NEURO_BUS_BRIDGE_MOD_ID, str(mod_dir)
    return None, None


def register_domain_handlers_via_mod(bus) -> dict[str, Any]:
    mod_id, mod_path = _resolve_mod_path()
    if not mod_path:
        raise RuntimeError("neuro-bus bridge mod not installed")
    mod = _load_handler_providers_module(mod_path, mod_id or NEURO_BUS_BRIDGE_MOD_ID)
    fn = getattr(mod, "register_all_domain_handlers", None)
    if not callable(fn):
        raise RuntimeError("handler_providers missing register_all_domain_handlers")
    result = fn(bus)
    if not isinstance(result, dict):
        result = {"registered": [], "handler_count": 0}
    result["execution_path"] = f"mod:{NEURO_BUS_BRIDGE_MOD_ID}"
    return result


async def register_domain_handlers_for_runtime(bus) -> dict[str, Any] | None:
    """启动时注册扁平领域 handler（Mod 编排或宿主直挂）。"""
    if is_neuro_bus_handlers_via_mod_enabled():
        logger.info("NeuroBus handlers: registering via %s", NEURO_BUS_BRIDGE_MOD_ID)
        return register_domain_handlers_via_mod(bus)
    from app.neuro_bus.register_all_domains_complete import register_domain_handlers_only

    await register_domain_handlers_only(bus)
    return {"execution_path": "host.register_all_domains_complete"}


def list_neuro_bus_handler_registry() -> dict[str, Any]:
    via = is_neuro_bus_handlers_via_mod_enabled()
    catalog_summary: dict[str, Any] = {}
    mod_dir = _resolve_mod_dir()
    if mod_dir:
        try:
            mod_id, mod_path = _resolve_mod_path()
            if mod_path:
                mod = _load_handler_providers_module(mod_path, mod_id or NEURO_BUS_BRIDGE_MOD_ID)
                if hasattr(mod, "summarize_handler_catalog"):
                    catalog_summary = mod.summarize_handler_catalog()
        except Exception as exc:
            catalog_summary = {"error": str(exc)}
    return {
        "ok": True,
        "mod_id": NEURO_BUS_BRIDGE_MOD_ID,
        "handlers_via_mod": via,
        "execution_path": (
            f"mod:{NEURO_BUS_BRIDGE_MOD_ID}" if via else "host.register_domain_handlers_only"
        ),
        "delegate": "host.neuro_bus.domains.*_domain_handlers",
        "phase": "N",
        "catalog": catalog_summary,
    }


__all__ = [
    "is_neuro_bus_handlers_via_mod_enabled",
    "list_neuro_bus_handler_registry",
    "register_domain_handlers_for_runtime",
    "register_domain_handlers_via_mod",
]
