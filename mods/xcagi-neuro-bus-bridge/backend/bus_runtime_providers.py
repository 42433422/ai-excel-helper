# -*- coding: utf-8 -*-
"""里程碑 S：NeuroBus 运行时提供方入口。"""

from __future__ import annotations

from typing import Any

PROVIDER_ID = "mod:xcagi-neuro-bus-bridge"


def list_runtime_resolvers() -> list[str]:
    return ["create_bus_runtime_bundle"]


def create_bus_runtime_bundle() -> dict[str, Any]:
    from app.infrastructure.mods.mod_manager import import_mod_backend_py
    from app.mod_sdk.neuro_bus_compat import NEURO_BUS_BRIDGE_MOD_ID, _resolve_mod_dir

    mod_dir = _resolve_mod_dir()
    if not mod_dir:
        raise RuntimeError("xcagi-neuro-bus-bridge mod dir not found")
    mod = import_mod_backend_py(str(mod_dir), NEURO_BUS_BRIDGE_MOD_ID, "bus_runtime_factory")
    return mod.create_bus_runtime_bundle()


__all__ = ["PROVIDER_ID", "list_runtime_resolvers", "create_bus_runtime_bundle"]
