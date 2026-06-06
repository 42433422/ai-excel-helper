"""FHD_DB_READ_TOKEN 与 /api/fhd/db-tokens/status（不加载 backend/tests/conftest 的 PG 门禁）。"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app.fastapi_routes.fhd_meta import router as fhd_meta_router
from app.fastapi_routes.xcagi_compat import router as xcagi_compat_router


@pytest.fixture(autouse=True)
def _skip_erp_domain_short_circuit(monkeypatch):
    """测试读锁逻辑时勿走 Mod ERP 分发（否则会绕过 verify_db_read_token）。"""
    monkeypatch.setattr(
        "app.mod_sdk.erp_domain_dispatch.try_invoke_erp_domain_handler",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "app.mod_sdk.erp_products_facade.is_erp_products_via_service_enabled",
        lambda: False,
    )


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.delenv("FHD_API_KEYS", raising=False)
    monkeypatch.delenv("AUDIT_LOG_PATH", raising=False)
    monkeypatch.delenv("FHD_DB_READ_TOKEN", raising=False)
    monkeypatch.delenv("FHD_DB_WRITE_TOKEN", raising=False)
    monkeypatch.delenv("FHD_DISABLE_DB_READ_LOCK", raising=False)
    app = FastAPI()
    app.include_router(fhd_meta_router)
    app.include_router(xcagi_compat_router, prefix="/api")
    with TestClient(app) as c:
        yield c


def test_db_tokens_status_all_false(client, monkeypatch):
    monkeypatch.setenv("FHD_DISABLE_DB_READ_LOCK", "1")
    r = client.get("/api/fhd/db-tokens/status")
    assert r.status_code == 200
    j = r.json()
    assert j["read_token_configured"] is False
    assert j["write_token_configured"] is False


def test_db_tokens_status_monkeypatch(client, monkeypatch):
    monkeypatch.setenv("FHD_DB_READ_TOKEN", "r")
    monkeypatch.setenv("FHD_DB_WRITE_TOKEN", "w")
    r = client.get("/api/fhd/db-tokens/status")
    assert r.status_code == 200
    j = r.json()
    assert j["read_token_configured"] is True
    assert j["write_token_configured"] is True


def test_products_list_403_when_read_token_configured_missing_header(client, monkeypatch):
    monkeypatch.setenv("FHD_DB_READ_TOKEN", "secret-read")
    r = client.get("/api/products/list")
    assert r.status_code == 403
    assert "只读" in (r.json().get("detail") or "")


def test_products_list_ok_with_read_header_mocked_pg(client, monkeypatch):
    monkeypatch.setenv("FHD_DB_READ_TOKEN", "secret-read")
    monkeypatch.setattr(
        "app.fastapi_routes.xcagi_compat_product._load_products_list_impl_pg",
        lambda *a, **k: ([], 0, None),
    )
    r = client.get(
        "/api/products/list",
        headers={"X-FHD-Db-Read-Token": "secret-read"},
    )
    assert r.status_code == 200
    assert r.json().get("success") is True


def test_customers_list_403_bad_read_token(client, monkeypatch):
    monkeypatch.setenv("FHD_DB_READ_TOKEN", "x")
    r = client.get("/api/customers/list", headers={"X-FHD-Db-Read-Token": "y"})
    assert r.status_code == 403


def test_products_list_200_when_read_token_unconfigured_no_header(client, monkeypatch):
    """未配置 FHD_DB_READ_TOKEN 时不启用一级读锁，可无头访问 list。"""
    monkeypatch.delenv("FHD_DISABLE_DB_READ_LOCK", raising=False)
    monkeypatch.delenv("FHD_DB_READ_TOKEN", raising=False)
    monkeypatch.delenv("FHD_DB_WRITE_TOKEN", raising=False)
    monkeypatch.setattr(
        "app.fastapi_routes.xcagi_compat_product._load_products_list_impl_pg",
        lambda *a, **k: ([], 0, None),
    )
    r = client.get("/api/products/list?page=1&per_page=1")
    assert r.status_code == 200
    assert r.json().get("success") is True
