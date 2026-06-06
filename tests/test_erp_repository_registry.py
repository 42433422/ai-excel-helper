# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MOD_DIR = REPO / "mods" / "xcagi-erp-domain-bridge"


def test_manifest_repository_via_mod():
    data = json.loads((MOD_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert data.get("config", {}).get("repository_via_mod") is True
    assert (MOD_DIR / "backend" / "repository_providers.py").is_file()
    assert (MOD_DIR / "backend" / "repository_adapters.py").is_file()


def test_repository_providers_return_adapter():
    from app.infrastructure.mods.mod_manager import import_mod_backend_py

    mod = import_mod_backend_py(str(MOD_DIR), "xcagi-erp-domain-bridge", "repository_providers")
    repo = mod.get_products_repository()
    assert repo is not None
    assert type(repo).__name__ == "ModProductRepositoryAdapter"


def test_resolve_products_repository_host_path(monkeypatch):
    from app.mod_sdk import erp_repository_registry as reg

    monkeypatch.setattr(reg, "is_erp_repository_via_mod_enabled", lambda: False)
    repo, provider = reg.resolve_products_repository()
    assert "SQLAlchemyProductRepository" in type(repo).__name__
    assert provider == "host:persistence"


def test_resolve_products_repository_mod_path(monkeypatch):
    from app.mod_sdk import erp_repository_registry as reg

    monkeypatch.setattr(reg, "is_erp_repository_via_mod_enabled", lambda: True)
    reg._load_repository_providers_module.cache_clear()
    repo, provider = reg.resolve_products_repository()
    assert type(repo).__name__ == "ModProductRepositoryAdapter"
    assert provider == f"mod:{reg.ERP_DOMAIN_BRIDGE_MOD_ID}"
    assert repo.meta().get("adapter_kind") == "mod_delegated"


def test_repository_adapters_module():
    from app.infrastructure.mods.mod_manager import import_mod_backend_py

    mod = import_mod_backend_py(str(MOD_DIR), "xcagi-erp-domain-bridge", "repository_adapters")
    adapter = mod.ModProductRepositoryAdapter()
    assert adapter.meta()["adapter_class"] == "ModProductRepositoryAdapter"
    assert hasattr(adapter, "find_all")


def test_list_erp_repository_registry_mod(monkeypatch):
    from app.mod_sdk import erp_repository_registry as reg

    monkeypatch.setattr(reg, "is_erp_repository_via_mod_enabled", lambda: True)
    reg._load_repository_providers_module.cache_clear()
    data = reg.list_erp_repository_registry()
    assert data.get("repository_via_mod") is True
    assert data.get("phase") == "L++"
    assert data.get("repository_adapter") == "mod_factory"
    assert "ModCustomersSessionAdapter" in (data.get("adapter_classes") or [])


def test_resolve_customers_session_mod_path(monkeypatch):
    from app.mod_sdk import erp_repository_registry as reg

    monkeypatch.setattr(reg, "is_erp_repository_via_mod_enabled", lambda: True)
    reg._load_repository_providers_module.cache_clear()
    session = reg.resolve_customers_session()
    assert session is not None
    assert hasattr(session, "query") or hasattr(session, "execute")


def test_repository_factory_bundle():
    from app.infrastructure.mods.mod_manager import import_mod_backend_py

    mod = import_mod_backend_py(str(MOD_DIR), "xcagi-erp-domain-bridge", "repository_factory")
    bundle = mod.create_repository_bundle()
    assert bundle.get("phase") == "L++"
    assert type(bundle["products"]).__name__ == "ModProductRepositoryAdapter"
    assert type(bundle["customers_session"]).__name__ == "ModCustomersSessionAdapter"
