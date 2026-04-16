"""GET /api/sales-contract/template-preview：读锁与 JSON 结构（构建逻辑 monkeypatch）。"""

import pytest
from starlette.testclient import TestClient

from backend import http_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("FHD_API_KEYS", raising=False)
    monkeypatch.delenv("AUDIT_LOG_PATH", raising=False)
    monkeypatch.setenv("FHD_DISABLE_DB_READ_LOCK", "1")
    with TestClient(http_app.app) as c:
        yield c


def test_sales_contract_template_preview_ok_when_mocked(client, monkeypatch):
    def _fake(slug: str | None = None):
        return {
            "success": True,
            "headers": ["客户名称", "品名"],
            "sample_rows": [{"客户名称": "示例", "品名": "A"}],
            "sheet_name": "Word 销售合同（首表）",
            "template_hint": "424/document_templates/example.docx",
        }

    monkeypatch.setattr(
        "backend.price_list_docx_export.build_sales_contract_template_preview_json",
        _fake,
    )
    r = client.get("/api/sales-contract/template-preview", params={"template_id": "tpl-a"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True
    assert body.get("headers") == ["客户名称", "品名"]
    assert isinstance(body.get("sample_rows"), list)


def test_sales_contract_template_preview_read_lock(monkeypatch):
    monkeypatch.delenv("FHD_DISABLE_DB_READ_LOCK", raising=False)
    monkeypatch.setenv("FHD_DB_READ_TOKEN", "read-secret-test")

    def _fake(slug: str | None = None):
        return {"success": True, "headers": ["A"], "sample_rows": [{}], "sheet_name": "S", "template_hint": "x"}

    monkeypatch.setattr(
        "backend.price_list_docx_export.build_sales_contract_template_preview_json",
        _fake,
    )

    with TestClient(http_app.app) as c:
        r0 = c.get("/api/sales-contract/template-preview")
        assert r0.status_code == 403

        r1 = c.get(
            "/api/sales-contract/template-preview",
            headers={"X-FHD-Db-Read-Token": "read-secret-test"},
        )
        assert r1.status_code == 200
        assert r1.json().get("success") is True
