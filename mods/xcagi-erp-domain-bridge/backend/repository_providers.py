# -*- coding: utf-8 -*-
"""里程碑 L / L+ / L++：ERP Repository 提供方。"""

from __future__ import annotations

from typing import Any

PROVIDER_ID = "mod:xcagi-erp-domain-bridge"
DELEGATE = "host.sqlalchemy"
PHASE = "L++"


def _load_adapters():
    from app.infrastructure.mods.mod_manager import import_mod_backend_py
    from app.mod_sdk.erp_domain_compat import ERP_DOMAIN_BRIDGE_MOD_ID, _resolve_mod_dir

    mod_dir = _resolve_mod_dir()
    if not mod_dir:
        raise RuntimeError("xcagi-erp-domain-bridge mod dir not found")
    return import_mod_backend_py(str(mod_dir), ERP_DOMAIN_BRIDGE_MOD_ID, "repository_adapters")


def _load_factory():
    from app.infrastructure.mods.mod_manager import import_mod_backend_py
    from app.mod_sdk.erp_domain_compat import ERP_DOMAIN_BRIDGE_MOD_ID, _resolve_mod_dir

    mod_dir = _resolve_mod_dir()
    if not mod_dir:
        raise RuntimeError("xcagi-erp-domain-bridge mod dir not found")
    return import_mod_backend_py(str(mod_dir), ERP_DOMAIN_BRIDGE_MOD_ID, "repository_factory")


def list_repository_resolvers() -> list[str]:
    return [
        "get_products_repository",
        "get_shipment_repository",
        "get_customers_session",
        "create_repository_bundle",
    ]


def list_adapter_classes() -> list[str]:
    return _load_adapters().list_adapter_classes()


def create_repository_bundle() -> dict[str, Any]:
    return _load_factory().create_repository_bundle()


def get_products_repository() -> Any:
    bundle = create_repository_bundle()
    return bundle["products"]


def get_shipment_repository() -> Any:
    bundle = create_repository_bundle()
    return bundle["shipment"]


def get_customers_session():
    bundle = create_repository_bundle()
    return bundle["customers_session"].resolve()
