# -*- coding: utf-8 -*-
"""里程碑 L++：统一仓储装配入口（宿主仅通过 registry 调用本 Mod）。"""

from __future__ import annotations

from typing import Any

PROVIDER_ID = "mod:xcagi-erp-domain-bridge"
FACTORY_PHASE = "L++"


def _load_adapters():
    from app.infrastructure.mods.mod_manager import import_mod_backend_py
    from app.mod_sdk.erp_domain_compat import ERP_DOMAIN_BRIDGE_MOD_ID, _resolve_mod_dir

    mod_dir = _resolve_mod_dir()
    if not mod_dir:
        raise RuntimeError("xcagi-erp-domain-bridge mod dir not found")
    return import_mod_backend_py(str(mod_dir), ERP_DOMAIN_BRIDGE_MOD_ID, "repository_adapters")


def create_repository_bundle() -> dict[str, Any]:
    """返回 products/shipment 仓储与客户 session 解析器。"""
    adapters = _load_adapters()
    return {
        "provider_id": PROVIDER_ID,
        "phase": FACTORY_PHASE,
        "products": adapters.ModProductRepositoryAdapter(),
        "shipment": adapters.ModShipmentRepositoryAdapter(),
        "customers_session": adapters.ModCustomersSessionAdapter(),
    }


__all__ = ["PROVIDER_ID", "FACTORY_PHASE", "create_repository_bundle"]
