# -*- coding: utf-8 -*-
"""里程碑 S：NeuroBus 生命周期与发布经 Mod 运行时 bundle 解析。"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from app.mod_sdk.neuro_bus_compat import NEURO_BUS_BRIDGE_MOD_ID, is_neuro_bus_via_mod_enabled

logger = logging.getLogger(__name__)


def is_neuro_bus_runtime_via_mod_enabled() -> bool:
    return is_neuro_bus_via_mod_enabled()


@lru_cache(maxsize=4)
def _load_runtime_providers(mod_path: str, mod_id: str):
    from app.infrastructure.mods.mod_manager import import_mod_backend_py

    return import_mod_backend_py(mod_path, mod_id, "bus_runtime_providers")


def _resolve_mod_path() -> tuple[str, str] | tuple[None, None]:
    try:
        from app.mod_sdk.neuro_bus_compat import _resolve_mod_dir

        mod_dir = _resolve_mod_dir()
        if mod_dir:
            return NEURO_BUS_BRIDGE_MOD_ID, str(mod_dir)
    except Exception:
        logger.debug("neuro bus runtime mod path failed", exc_info=True)
    return None, None


def _get_bundle() -> dict[str, Any]:
    mod_id, mod_path = _resolve_mod_path()
    if not mod_path:
        raise RuntimeError("neuro bus runtime mod not installed")
    mod = _load_runtime_providers(mod_path, mod_id or NEURO_BUS_BRIDGE_MOD_ID)
    return mod.create_bus_runtime_bundle()


async def run_lifespan_setup() -> None:
    if not is_neuro_bus_runtime_via_mod_enabled():
        from app.neuro_bus.bus_setup import setup_neuro_bus
        from app.neuro_bus.domains.base import get_domain_registry

        await setup_neuro_bus()
        await get_domain_registry().initialize_all()
        return
    bundle = _get_bundle()
    await bundle["setup"]()


async def run_lifespan_teardown() -> None:
    if not is_neuro_bus_runtime_via_mod_enabled():
        from app.neuro_bus.bus_setup import teardown_neuro_bus
        from app.neuro_bus.domains.base import get_domain_registry

        try:
            await get_domain_registry().shutdown_all()
        finally:
            await teardown_neuro_bus()
        return
    bundle = _get_bundle()
    await bundle["teardown"]()


def _host_publish(event_type: str, payload: dict[str, Any], domain: str) -> bool:
    from app.neuro_bus.bus import get_neuro_bus
    from app.neuro_bus.events.base import EventPriority, NeuroEvent

    bus = get_neuro_bus()
    if not bus.is_running:
        return False
    ev = NeuroEvent(
        event_type=event_type,
        payload=payload,
        priority=EventPriority.NORMAL,
    )
    ev.with_domain(domain)
    return bool(bus.publish(ev))


def publish_neuro_event_runtime(
    event_type: str, payload: dict[str, Any], domain: str = "global"
) -> bool:
    if not is_neuro_bus_runtime_via_mod_enabled():
        return _host_publish(event_type, payload, domain)
    bundle = _get_bundle()
    return bool(bundle["publish"](event_type, payload, domain))


def get_neuro_bus_health_runtime() -> dict[str, Any]:
    if not is_neuro_bus_runtime_via_mod_enabled():
        from app.neuro_bus.bus_setup import get_neuro_bus_manager

        manager = get_neuro_bus_manager()
        return manager.get_health() if manager else {}
    bundle = _get_bundle()
    return bundle["health"]()


__all__ = [
    "is_neuro_bus_runtime_via_mod_enabled",
    "run_lifespan_setup",
    "run_lifespan_teardown",
    "publish_neuro_event_runtime",
    "get_neuro_bus_health_runtime",
]
