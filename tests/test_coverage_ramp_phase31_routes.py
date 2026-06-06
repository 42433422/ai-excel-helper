"""COVERAGE_RAMP Phase 31: xcagi_compat_customer routes (mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.fastapi_routes.domains.customer import routes as customer_compat
from app.fastapi_routes.domains.customer import routes as customer_routes


@pytest.fixture
def compat_customer_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(
        customer_routes,
        "_load_customers_rows",
        lambda: [{"id": 1, "unit_name": "七彩乐园"}],
    )
    monkeypatch.setattr(customer_routes, "_business_mod_json_block", lambda: False)
    app = FastAPI()
    app.include_router(customer_compat.router)
    return TestClient(app, raise_server_exceptions=False)


def test_compat_customers_all_and_list(compat_customer_client: TestClient) -> None:
    r1 = compat_customer_client.get("/customers", params={"keyword": "彩"})
    assert r1.status_code == 200
    assert r1.json()["success"] is True
    assert len(r1.json()["data"]) == 1
    r2 = compat_customer_client.get("/customers/list", params={"page": 1, "per_page": 10})
    assert r2.status_code == 200


def test_compat_customers_match_empty(compat_customer_client: TestClient) -> None:
    r = compat_customer_client.get("/customers/match")
    assert r.status_code == 200
    assert r.json()["matched"] is None


def test_compat_customers_match_with_extract(
    compat_customer_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.infrastructure.products.customer_matching.extract_customer_name",
        lambda s: "七彩" if "乐园" in s else None,
    )
    monkeypatch.setattr(
        "app.infrastructure.products.customer_matching.find_matching_customer",
        lambda s: "七彩乐园" if s else "",
    )
    r = compat_customer_client.get(
        "/customers/match",
        params={"customer_name": "去七彩乐园拿货"},
    )
    assert r.status_code == 200
    assert r.json()["matched"] == "七彩乐园"


def test_compat_customers_match_mod_block(
    compat_customer_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(customer_routes, "_business_mod_json_block", lambda: True)
    r = compat_customer_client.get("/customers/match", params={"customer_name": "X"})
    assert r.json()["matched"] is None


def test_compat_customer_get_one_and_create(compat_customer_client: TestClient) -> None:
    row = MagicMock()
    row.id = 2
    with (
        patch(
            "app.mod_sdk.erp_customers_facade.is_erp_customers_via_service_enabled",
            return_value=False,
        ),
        patch.object(customer_routes, "_customer_find_by_id", return_value=row),
        patch.object(
            customer_routes,
            "_customer_row_for_api",
            return_value={"id": 2, "unit_name": "A"},
        ),
        patch.object(customer_routes, "_customers_write_raise"),
        patch.object(
            customer_routes,
            "_customer_pg_insert",
            return_value={"id": 3, "unit_name": "B"},
        ),
        patch.object(
            customer_routes, "_customer_body_name_contact", return_value=("B", "", "", "")
        ),
    ):
        assert compat_customer_client.get("/customers/2").status_code == 200
        created = compat_customer_client.post("/customers", json={"unit_name": "B"})
        assert created.status_code == 200
        assert created.json()["data"]["id"] == 3


def test_compat_customer_batch_delete(compat_customer_client: TestClient) -> None:
    with (
        patch.object(customer_routes, "_customers_write_raise"),
        patch.object(customer_routes, "_customer_delete_unified"),
    ):
        batch = compat_customer_client.post("/customers/batch-delete", json={"ids": [2, 3]})
    assert batch.status_code == 200
    assert batch.json()["deleted"] == 2
