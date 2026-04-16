"""受令牌保护的产品批量导入 API。"""

from __future__ import annotations


def test_admin_bulk_import_503_when_token_unconfigured(client, monkeypatch):
    monkeypatch.delenv("FHD_DB_WRITE_TOKEN", raising=False)
    r = client.post(
        "/api/admin/products/bulk-import",
        json={"customer_name": "某公司", "items": [{"name": "产品A", "price": 1.0}]},
    )
    assert r.status_code == 503


def test_admin_bulk_import_403_bad_header(client, monkeypatch):
    monkeypatch.setenv("FHD_DB_WRITE_TOKEN", "secret-token")
    r = client.post(
        "/api/admin/products/bulk-import",
        json={"customer_name": "某公司", "items": [{"name": "产品A", "price": 1.0}]},
        headers={"X-FHD-Db-Write-Token": "wrong"},
    )
    assert r.status_code == 403


def test_admin_bulk_import_400_empty_items(client, monkeypatch):
    monkeypatch.setenv("FHD_DB_WRITE_TOKEN", "t")
    r = client.post(
        "/api/admin/products/bulk-import",
        json={"customer_name": "某公司", "items": []},
        headers={"X-FHD-Db-Write-Token": "t"},
    )
    assert r.status_code == 400


def test_admin_bulk_import_200_delegates(client, monkeypatch):
    monkeypatch.setenv("FHD_DB_WRITE_TOKEN", "tok")

    def fake_run(body: dict):
        fake_run.seen = body
        return {
            "success": True,
            "customer_name": body.get("customer_name"),
            "inserted": 1,
            "updated": 0,
            "deleted": 0,
            "purchase_unit_created": False,
            "replace": False,
            "errors": [],
        }

    monkeypatch.setattr("backend.routers.products_admin.run_bulk_import", fake_run)
    r = client.post(
        "/api/admin/products/bulk-import",
        json={
            "customer_name": "惠州市鸿瑞达家具有限公司",
            "items": [{"model_number": "6821A", "name": "PE白底漆", "specification": "30KG/桶", "price": 14.56}],
            "supplier_name": "深圳市奇士美涂料有限公司",
            "quote_date": "2026-04-01",
        },
        headers={"X-FHD-Db-Write-Token": "tok"},
    )
    assert r.status_code == 200
    j = r.json()
    assert j.get("success") is True
    assert j["data"]["inserted"] == 1
    assert fake_run.seen["customer_name"] == "惠州市鸿瑞达家具有限公司"


def test_execute_workflow_tool_products_bulk_import_unauthorized(monkeypatch):
    import json

    monkeypatch.setenv("FHD_DB_WRITE_TOKEN", "srv")
    from backend.tools import execute_workflow_tool

    raw = execute_workflow_tool(
        "products_bulk_import",
        {
            "customer_name": "c",
            "items": [{"name": "p", "price": 1}],
        },
        workspace_root=".",
        db_write_token=None,
    )
    out = json.loads(raw)
    assert out.get("error") == "unauthorized"


def test_execute_workflow_tool_products_bulk_import_ok(monkeypatch):
    import json

    monkeypatch.setenv("FHD_DB_WRITE_TOKEN", "srv")
    from backend.tools import execute_workflow_tool

    monkeypatch.setattr(
        "backend.products_bulk_import.run_bulk_import",
        lambda body: {"success": True, "inserted": 2, "errors": []},
    )
    raw = execute_workflow_tool(
        "products_bulk_import",
        {"customer_name": "c", "items": [{"name": "p", "price": 1}]},
        workspace_root=".",
        db_write_token="srv",
    )
    out = json.loads(raw)
    assert out.get("success") is True
    assert out.get("inserted") == 2
