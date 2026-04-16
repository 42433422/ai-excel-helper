"""
无 PostgreSQL 依赖的形状校验（不放在 backend/tests/ 下，以免继承 tests/conftest 的库级 Skip）。
运行：pytest backend/test_products_bulk_import_shapes.py -q
"""

from __future__ import annotations

import json

from backend.products_bulk_import import run_bulk_import
from backend.tools import execute_workflow_tool, get_workflow_tool_registry


def test_run_bulk_import_rejects_empty_items():
    out = run_bulk_import({"customer_name": "测试客户", "items": []})
    assert out.get("success") is False
    assert out.get("error") == "empty_items"


def test_run_bulk_import_rejects_missing_customer():
    out = run_bulk_import({"customer_name": "", "items": [{"name": "A"}]})
    assert out.get("success") is False
    assert out.get("error") == "missing_customer_name"


def test_products_bulk_import_tool_unauthorized_without_token(monkeypatch):
    monkeypatch.setenv("FHD_DB_WRITE_TOKEN", "server-secret")
    import backend.tools as tools_mod

    tools_mod._workflow_tool_registry_cache = None
    tools_mod._workflow_tool_registry_bulk_token_present = None
    raw = execute_workflow_tool(
        "products_bulk_import",
        {"customer_name": "U", "items": [{"name": "P", "price": 1}]},
        workspace_root=".",
        db_write_token=None,
    )
    data = json.loads(raw)
    assert data.get("error") == "unauthorized"


def test_workflow_tool_registry_rebuilds_when_write_token_env_changes(monkeypatch):
    import backend.tools as tools_mod

    monkeypatch.delenv("FHD_DB_WRITE_TOKEN", raising=False)
    tools_mod._workflow_tool_registry_cache = None
    tools_mod._workflow_tool_registry_bulk_token_present = None

    reg_off = get_workflow_tool_registry()
    names_off = {t.get("function", {}).get("name") for t in reg_off}

    monkeypatch.setenv("FHD_DB_WRITE_TOKEN", "t")
    reg_on = get_workflow_tool_registry()
    names_on = {t.get("function", {}).get("name") for t in reg_on}

    assert "products_bulk_import" not in names_off
    assert "products_bulk_import" in names_on
