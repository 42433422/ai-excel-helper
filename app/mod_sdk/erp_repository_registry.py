# -*- coding: utf-8 -*-
"""里程碑 L：ERP 领域 Repository 经 ``xcagi-erp-domain-bridge`` 提供方装配（可插拔边界）。"""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from typing import Any

from app.mod_sdk.erp_domain_compat import ERP_DOMAIN_BRIDGE_MOD_ID, _read_manifest, _resolve_mod_dir

logger = logging.getLogger(__name__)

REPOSITORY_SPECS: tuple[dict[str, str], ...] = (
    {"domain_id": "products", "port": "ProductRepository", "resolver": "get_products_repository"},
    {"domain_id": "shipment", "port": "ShipmentRepository", "resolver": "get_shipment_repository"},
    {
        "domain_id": "customers",
        "port": "SessionLocal (mod-aware)",
        "resolver": "get_customers_session",
        "note": "客户领域仍经 CustomerApplicationService + app.db Mod 上下文，无独立 Repository 类",
    },
)


def _truthy_env(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def is_erp_repository_via_mod_enabled() -> bool:
    if _truthy_env("XCAGI_DISABLE_ERP_REPOSITORY_MOD"):
        return False
    if _truthy_env("XCAGI_ERP_REPOSITORY_VIA_MOD"):
        return True
    cfg = _read_manifest().get("config") or {}
    if isinstance(cfg, dict) and cfg.get("repository_via_mod") is True:
        return True
    return False


@lru_cache(maxsize=4)
def _load_repository_providers_module(mod_path: str, mod_id: str):
    from app.infrastructure.mods.mod_manager import import_mod_backend_py

    return import_mod_backend_py(mod_path, mod_id, "repository_providers")


def _resolve_mod_path() -> tuple[str, str] | tuple[None, None]:
    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager

        meta = get_mod_manager().get_mod(ERP_DOMAIN_BRIDGE_MOD_ID)
        if meta and meta.mod_path:
            return ERP_DOMAIN_BRIDGE_MOD_ID, str(meta.mod_path)
    except Exception:
        logger.debug("erp repository mod path via manager failed", exc_info=True)
    mod_dir = _resolve_mod_dir()
    if mod_dir:
        return ERP_DOMAIN_BRIDGE_MOD_ID, str(mod_dir)
    return None, None


def _call_mod_resolver(fn_name: str) -> Any:
    mod_id, mod_path = _resolve_mod_path()
    if not mod_path:
        raise RuntimeError("erp repository mod not installed")
    mod = _load_repository_providers_module(mod_path, mod_id or ERP_DOMAIN_BRIDGE_MOD_ID)
    fn = getattr(mod, fn_name, None)
    if not callable(fn):
        raise RuntimeError(f"repository_providers missing {fn_name}")
    return fn()


def _host_products_repository():
    from app.infrastructure.persistence.product_repository_impl import SQLAlchemyProductRepository

    return SQLAlchemyProductRepository()


def _host_shipment_repository():
    from app.infrastructure.repositories.shipment_repository_impl import (
        SQLAlchemyShipmentRepository,
    )

    return SQLAlchemyShipmentRepository()


def resolve_products_repository() -> tuple[Any, str]:
    if not is_erp_repository_via_mod_enabled():
        return _host_products_repository(), "host:persistence"
    return _call_mod_resolver("get_products_repository"), f"mod:{ERP_DOMAIN_BRIDGE_MOD_ID}"


def resolve_shipment_repository() -> tuple[Any, str]:
    if not is_erp_repository_via_mod_enabled():
        return _host_shipment_repository(), "host:repositories"
    return _call_mod_resolver("get_shipment_repository"), f"mod:{ERP_DOMAIN_BRIDGE_MOD_ID}"


def _host_customers_session():
    from app.db import SessionLocal

    return SessionLocal()


def resolve_customers_session():
    """L++：客户域 session 经 Mod 适配器解析（仍 mod-aware SessionLocal）。"""
    if not is_erp_repository_via_mod_enabled():
        return _host_customers_session()
    return _call_mod_resolver("get_customers_session")


def get_repository_execution_meta(domain_id: str) -> dict[str, str]:
    dom = str(domain_id or "").strip()
    if dom == "products" and is_erp_repository_via_mod_enabled():
        return {
            "repository_provider": f"mod:{ERP_DOMAIN_BRIDGE_MOD_ID}",
            "storage_path": "mod_delegated_adapter",
            "adapter_kind": "mod_delegated",
        }
    if dom == "shipment" and is_erp_repository_via_mod_enabled():
        return {
            "repository_provider": f"mod:{ERP_DOMAIN_BRIDGE_MOD_ID}",
            "storage_path": "mod_delegated_adapter",
            "adapter_kind": "mod_delegated",
        }
    if dom == "customers" and is_erp_repository_via_mod_enabled():
        return {
            "repository_provider": f"mod:{ERP_DOMAIN_BRIDGE_MOD_ID}",
            "storage_path": "mod_session_facade",
            "adapter_kind": "mod_session_facade",
        }
    if dom == "customers":
        return {
            "repository_provider": "host:app.db.SessionLocal",
            "storage_path": "mod_aware_engine",
        }
    return {}


def list_erp_repository_registry() -> dict[str, Any]:
    via = is_erp_repository_via_mod_enabled()
    mod_id, mod_path = _resolve_mod_path()
    resolvers: list[str] = []
    adapters: list[str] = []
    if mod_path and via:
        try:
            mod = _load_repository_providers_module(mod_path, mod_id or ERP_DOMAIN_BRIDGE_MOD_ID)
            reg = getattr(mod, "list_repository_resolvers", None)
            if callable(reg):
                resolvers = list(reg())
            list_adapters = getattr(mod, "list_adapter_classes", None)
            if callable(list_adapters):
                adapters = list(list_adapters())
            if not adapters:
                try:
                    from app.infrastructure.mods.mod_manager import import_mod_backend_py

                    adapters_mod = import_mod_backend_py(
                        mod_path, mod_id or ERP_DOMAIN_BRIDGE_MOD_ID, "repository_adapters"
                    )
                    list_fn = getattr(adapters_mod, "list_adapter_classes", None)
                    if callable(list_fn):
                        adapters = list(list_fn())
                except Exception:
                    pass
        except Exception:
            logger.debug("list_repository_resolvers failed", exc_info=True)
    cfg = _read_manifest().get("config") or {}
    adapter_kind = cfg.get("repository_adapter") if isinstance(cfg, dict) else None
    repo_phase = cfg.get("repository_phase") if isinstance(cfg, dict) else None
    phase = repo_phase or (cfg.get("phase") if isinstance(cfg, dict) else "L")
    factory_resolver = "create_repository_bundle" in resolvers
    return {
        "ok": True,
        "mod_id": ERP_DOMAIN_BRIDGE_MOD_ID,
        "repository_via_mod": via,
        "repository_adapter": adapter_kind
        or ("mod_factory" if via and factory_resolver else ("mod_delegated" if via else None)),
        "adapter_classes": adapters,
        "execution_path": (
            "mod_factory_bundle"
            if via and factory_resolver
            else ("mod_delegated_adapter" if via else "host.wiring")
        ),
        "domains": [dict(s) for s in REPOSITORY_SPECS],
        "resolver_count": len(resolvers) or len(REPOSITORY_SPECS),
        "resolvers": resolvers or [s["resolver"] for s in REPOSITORY_SPECS],
        "phase": phase,
        "note": "里程碑 L++：统一 create_repository_bundle；客户 session 经 ModCustomersSessionAdapter。",
    }


__all__ = [
    "ERP_DOMAIN_BRIDGE_MOD_ID",
    "REPOSITORY_SPECS",
    "get_repository_execution_meta",
    "is_erp_repository_via_mod_enabled",
    "list_erp_repository_registry",
    "resolve_products_repository",
    "resolve_shipment_repository",
    "resolve_customers_session",
]
