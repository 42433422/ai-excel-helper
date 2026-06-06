# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MOD_DIR = REPO / "mods" / "xcagi-erp-domain-bridge"


def test_erp_domain_mod_manifest():
    data = json.loads((MOD_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert data["id"] == "xcagi-erp-domain-bridge"
    assert data.get("config", {}).get("erp_domain_facade") is True


def test_erp_domains_config():
    cfg = json.loads((MOD_DIR / "config" / "erp_domains.json").read_text(encoding="utf-8"))
    ids = {d["id"] for d in cfg.get("domains", [])}
    assert {"products", "customers", "shipment", "wechat"} <= ids


def test_blueprints_has_products_and_wechat():
    text = (MOD_DIR / "backend" / "blueprints.py").read_text(encoding="utf-8")
    assert "/products/list" in text
    assert "/wechat/contacts" in text
    assert "/domains/registry" in text
    assert "mount_wechat_contacts_routes" in text


def test_list_erp_domains_registry_host(monkeypatch):
    from app.mod_sdk import erp_domain_compat as ed

    monkeypatch.setattr(ed, "is_erp_domain_via_mod_enabled", lambda: False)
    data = ed.list_erp_domains_registry()
    assert data.get("ok") is True
    assert data.get("execution_path") == "host.api"
    assert data.get("domain_count") == 4


def test_list_erp_domains_registry_mod_facade(monkeypatch):
    from app.mod_sdk import erp_domain_compat as ed

    monkeypatch.setattr(ed, "is_erp_domain_via_mod_enabled", lambda: True)
    data = ed.list_erp_domains_registry()
    assert data.get("execution_via_mod_facade") is True
    assert "xcagi-erp-domain-bridge" in str(data.get("registry_endpoint"))


def test_resolve_host_api_path():
    from app.mod_sdk.erp_domain_compat import ERP_DOMAIN_BRIDGE_MOD_ID, resolve_host_api_path

    facade = f"/api/mod/{ERP_DOMAIN_BRIDGE_MOD_ID}/products/list"
    assert resolve_host_api_path(facade) == "/api/products/list"


def test_platform_shell_includes_erp_bridge():
    from app.mod_sdk.platform_shell import BRIDGE_MOD_HOST_APIS

    assert "xcagi-erp-domain-bridge" in BRIDGE_MOD_HOST_APIS


def test_manifest_mod_domain_handlers():
    data = json.loads((MOD_DIR / "manifest.json").read_text(encoding="utf-8"))
    handlers = data.get("config", {}).get("mod_domain_handlers") or []
    assert {"products", "shipment", "customers", "wechat"} <= set(handlers)
    from tests.mod_sdk_expectations import ERP_PHASE_TOKENS, ERP_REPOSITORY_ADAPTERS

    cfg = data.get("config", {})
    phase = cfg.get("phase") or cfg.get("repository_phase") or ""
    assert phase in ERP_PHASE_TOKENS
    assert cfg.get("repository_adapter") in ERP_REPOSITORY_ADAPTERS
    assert data.get("config", {}).get("erp_extended_pages") is True
    assert data.get("config", {}).get("products_via_service") is True
    assert data.get("config", {}).get("customers_via_service") is True


def test_domain_handlers_products_list(monkeypatch):
    from app.infrastructure.mods.mod_manager import import_mod_backend_py

    mod = import_mod_backend_py(str(MOD_DIR), "xcagi-erp-domain-bridge", "domain_handlers")
    monkeypatch.setattr(
        "app.mod_sdk.erp_products_facade.is_erp_products_via_service_enabled",
        lambda: False,
    )
    monkeypatch.setattr(
        "app.fastapi_routes.xcagi_compat_db_product_queries._load_products_list_impl_pg",
        lambda page, per_page, keyword, unit: ([{"id": 1, "name": "A"}], 1, None),
    )
    monkeypatch.setattr(
        "app.infrastructure.auth.db_token.verify_db_read_token_header",
        lambda request: None,
    )
    out = mod.run_domain_handler("products", "list", page=1, per_page=20)
    assert out.get("success") is True
    assert out.get("source") == "mod:xcagi-erp-domain-bridge"
    assert out.get("execution_path") == "mod_domain_handler"


def test_domain_handlers_shipment_records(monkeypatch):
    from app.infrastructure.mods.mod_manager import import_mod_backend_py

    mod = import_mod_backend_py(str(MOD_DIR), "xcagi-erp-domain-bridge", "domain_handlers")

    class FakeShipment:
        def get_shipment_records(self, unit):
            return [{"id": 9, "unit_name": unit or "all"}]

    monkeypatch.setattr(
        "app.bootstrap.get_shipment_app_service",
        lambda: FakeShipment(),
    )
    out = mod.run_domain_handler("shipment", "records_list", unit="测试单位")
    assert out.get("success") is True
    assert out["data"][0]["id"] == 9
    assert out.get("source") == "mod:xcagi-erp-domain-bridge"


def test_try_invoke_products_list(monkeypatch):
    from app.mod_sdk import erp_domain_dispatch as ed

    monkeypatch.setattr(ed, "is_erp_domain_handlers_enabled", lambda: True)
    monkeypatch.setattr(ed, "_mod_domain_handler_domains", lambda: ["products", "shipment"])
    monkeypatch.setattr(
        ed,
        "_resolve_mod_path",
        lambda: ("xcagi-erp-domain-bridge", str(MOD_DIR)),
    )
    monkeypatch.setattr(
        "app.fastapi_routes.xcagi_compat_db_product_queries._load_products_list_impl_pg",
        lambda page, per_page, keyword, unit: ([], 0, None),
    )
    monkeypatch.setattr(
        "app.infrastructure.auth.db_token.verify_db_read_token_header",
        lambda request: None,
    )
    out = ed.try_invoke_erp_domain_handler("products", "list", page=1, per_page=10)
    assert out is not None
    assert out.get("source") == "mod:xcagi-erp-domain-bridge"


def test_registry_phase_g_domains(monkeypatch):
    from app.mod_sdk import erp_domain_compat as ed

    monkeypatch.setattr(ed, "is_erp_domain_via_mod_enabled", lambda: True)
    monkeypatch.setattr(
        ed,
        "_mod_handler_domains",
        lambda: {"products", "shipment", "customers", "wechat"},
    )
    data = ed.list_erp_domains_registry()
    assert data.get("execution_path") == "mod_domain_handler"
    for dom_id in ("products", "customers", "wechat"):
        row = next(d for d in data["domains"] if d["domain_id"] == dom_id)
        assert row.get("delegate") == "mod.domain_handlers"


def test_domain_handlers_customers_list(monkeypatch):
    from app.infrastructure.mods.mod_manager import import_mod_backend_py

    mod = import_mod_backend_py(str(MOD_DIR), "xcagi-erp-domain-bridge", "domain_handlers")
    monkeypatch.setattr(
        "app.mod_sdk.erp_customers_facade.is_erp_customers_via_service_enabled",
        lambda: False,
    )
    monkeypatch.setattr(
        "app.fastapi_routes.xcagi_compat_db_queries._load_customers_rows",
        lambda: [{"id": 1, "customer_name": "测试"}],
    )
    monkeypatch.setattr(
        "app.infrastructure.auth.db_token.verify_db_read_token_header",
        lambda request: None,
    )
    out = mod.run_domain_handler("customers", "list", page=1, per_page=10)
    assert out.get("success") is True
    assert out.get("total") == 1
    assert out.get("source") == "mod:xcagi-erp-domain-bridge"


def test_domain_handlers_wechat_contacts(monkeypatch):
    from app.infrastructure.mods.mod_manager import import_mod_backend_py

    mod = import_mod_backend_py(str(MOD_DIR), "xcagi-erp-domain-bridge", "domain_handlers")

    class FakeWechat:
        def get_contacts(self, **kwargs):
            return [{"id": 3, "contact_name": "张三"}]

    monkeypatch.setattr(
        "app.application.get_wechat_contact_app_service",
        lambda: FakeWechat(),
    )
    out = mod.run_domain_handler("wechat", "contacts_list", limit=50)
    assert out.get("success") is True
    assert out["data"][0]["id"] == 3
    assert out.get("source") == "mod:xcagi-erp-domain-bridge"
