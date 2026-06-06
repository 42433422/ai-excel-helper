# -*- coding: utf-8 -*-
"""里程碑 S：NeuroBus 运行时统一装配。"""

from __future__ import annotations

from typing import Any

PROVIDER_ID = "mod:xcagi-neuro-bus-bridge"
FACTORY_PHASE = "S"


def _load_adapters():
    from app.infrastructure.mods.mod_manager import import_mod_backend_py
    from app.mod_sdk.neuro_bus_compat import NEURO_BUS_BRIDGE_MOD_ID, _resolve_mod_dir

    mod_dir = _resolve_mod_dir()
    if not mod_dir:
        raise RuntimeError("xcagi-neuro-bus-bridge mod dir not found")
    return import_mod_backend_py(str(mod_dir), NEURO_BUS_BRIDGE_MOD_ID, "bus_runtime_adapters")


def create_bus_runtime_bundle() -> dict[str, Any]:
    adapter = _load_adapters().ModNeuroBusRuntimeAdapter()
    return {
        "provider_id": PROVIDER_ID,
        "phase": FACTORY_PHASE,
        "runtime": adapter,
        "setup": adapter.setup,
        "teardown": adapter.teardown,
        "publish": adapter.publish,
        "health": adapter.health,
    }


__all__ = ["PROVIDER_ID", "FACTORY_PHASE", "create_bus_runtime_bundle"]
