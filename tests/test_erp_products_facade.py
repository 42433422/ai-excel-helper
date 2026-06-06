# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MOD_DIR = REPO / "mods" / "xcagi-erp-domain-bridge"


def test_manifest_products_via_service():
    data = json.loads((MOD_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert data.get("config", {}).get("products_via_service") is True
    assert data.get("config", {}).get("products_via_service") is True


def test_products_list_via_service(monkeypatch):
    from app.mod_sdk import erp_products_facade as pf

    monkeypatch.setattr(pf, "is_erp_products_via_service_enabled", lambda: True)

    class FakeSvc:
        def get_products(self, **kwargs):
            return {"success": True, "data": [{"id": 1, "name": "P1"}], "total": 1}

    monkeypatch.setattr(pf, "_service", lambda: FakeSvc())
    monkeypatch.setattr(
        "app.infrastructure.auth.db_token.verify_db_read_token_header",
        lambda request: None,
    )
    out = pf.products_list(None, page=1, per_page=20)
    assert out["success"] is True
    assert out["total"] == 1
    assert out.get("execution_path") == "products_service"


def test_domain_handlers_products_list_uses_service(monkeypatch):
    from app.infrastructure.mods.mod_manager import import_mod_backend_py

    mod = import_mod_backend_py(str(MOD_DIR), "xcagi-erp-domain-bridge", "domain_handlers")
    monkeypatch.setattr(
        "app.mod_sdk.erp_products_facade.is_erp_products_via_service_enabled",
        lambda: True,
    )
    monkeypatch.setattr(
        "app.mod_sdk.erp_products_facade.products_list",
        lambda request, **kw: {
            "success": True,
            "data": [],
            "total": 0,
            "source": "mod:xcagi-erp-domain-bridge",
            "execution_path": "products_service",
        },
    )
    out = mod.run_domain_handler("products", "list", page=1, per_page=10)
    assert out.get("execution_path") == "mod_domain_handler"
    assert out.get("source") == "mod:xcagi-erp-domain-bridge"


def test_products_delete_via_service(monkeypatch):
    from app.mod_sdk import erp_products_facade as pf

    monkeypatch.setattr(pf, "is_erp_products_via_service_enabled", lambda: True)
    monkeypatch.setattr(pf, "_write_gate", lambda request: None)

    class FakeSvc:
        def delete_product(self, product_id):
            return {"success": True, "message": "产品删除成功"}

    monkeypatch.setattr(pf, "_service", lambda: FakeSvc())
    out = pf.products_delete(None, {"id": 42})
    assert out["success"] is True
    assert out.get("execution_path") == "products_service"
