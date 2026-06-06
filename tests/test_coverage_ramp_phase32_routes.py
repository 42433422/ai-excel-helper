"""COVERAGE_RAMP Phase 32: legacy_excel parse, xcagi_compat_product list (mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_legacy_excel_parse_single_empty() -> None:
    from app.fastapi_routes.domains.excel import routes as legacy_excel_mod

    app = FastAPI()
    app.include_router(legacy_excel_mod.router)
    client = TestClient(app, raise_server_exceptions=False)
    r = client.post("/api/ai/parse-single", json={"text": "  "})
    assert r.status_code == 400


def test_legacy_excel_parse_single_success(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.fastapi_routes.domains.excel import routes as legacy_excel_mod

    parser = MagicMock()
    parser.parse_single.return_value = {"success": True, "product": "螺栓"}
    monkeypatch.setattr(
        "app.application.facades.excel_facade.get_ai_product_parser",
        lambda: parser,
    )
    app = FastAPI()
    app.include_router(legacy_excel_mod.router)
    client = TestClient(app, raise_server_exceptions=False)
    r = client.post("/api/ai/parse-single", json={"text": "M8螺栓 100个"})
    assert r.status_code == 200
    assert r.json()["success"] is True


@pytest.fixture
def compat_product_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    from app.fastapi_routes.domains.product import compat_routes as product_compat

    monkeypatch.setattr(product_compat, "_business_mod_json_block", lambda: False)
    monkeypatch.setattr(
        "app.infrastructure.auth.db_token.verify_db_read_token_header",
        lambda _req: None,
    )
    app = FastAPI()
    app.include_router(product_compat.router)
    return TestClient(app, raise_server_exceptions=False)


def test_compat_products_list(compat_product_client: TestClient) -> None:
    with (
        patch(
            "app.mod_sdk.erp_domain_dispatch.try_invoke_erp_domain_handler",
            return_value=None,
        ),
        patch(
            "app.mod_sdk.erp_products_facade.is_erp_products_via_service_enabled",
            return_value=False,
        ),
        patch(
            "app.fastapi_routes.domains.product.compat_routes._load_products_list_impl_pg",
            return_value=([{"id": 1, "name": "螺丝"}], 1, None),
        ),
    ):
        r = compat_product_client.get("/products/list", params={"keyword": "螺"})
    assert r.status_code == 200
    assert r.json()["total"] == 1
