"""COVERAGE_RAMP Phase 41: approval, finance, shipment, customer, tools (mocked TestClient)."""

from __future__ import annotations

import json
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.approval import ApprovalFlow, ApprovalFlowNode, ApprovalStatus
from app.fastapi_routes import approval as approval_routes
from app.fastapi_routes import finance as finance_routes
from app.fastapi_routes import shipment_orders as shipment_routes
from app.fastapi_routes.domains.customer import routes as customer_compat
from app.fastapi_routes.domains.customer import routes as customer_routes
from app.fastapi_routes.domains.misc import routes as compat_misc
from app.fastapi_routes.domains.system import routes as legacy_system_routes

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def finance_client() -> TestClient:
    app = FastAPI()
    app.include_router(finance_routes.router)
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_shipment_svc() -> MagicMock:
    svc = MagicMock()
    svc.get_orders.return_value = [{"id": 1}]
    svc.generate_shipment_document.return_value = {
        "success": True,
        "file_path": "/tmp/p41.xlsx",
    }
    return svc


@pytest.fixture
def shipment_client(mock_shipment_svc: MagicMock, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(
        shipment_routes, "get_shipment_application_service_core", lambda: mock_shipment_svc
    )
    app = FastAPI()
    app.include_router(shipment_routes.router)
    return TestClient(app, raise_server_exceptions=False)


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


@pytest.fixture
def tools_client() -> TestClient:
    app = FastAPI()
    app.include_router(legacy_system_routes.router)
    app.include_router(compat_misc.router)
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def approval_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    yield session_factory
    session_factory().close()
    Base.metadata.drop_all(engine)
    engine.dispose()


@contextmanager
def _patch_get_db(session_factory):
    @contextmanager
    def _get_db():
        db = session_factory()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    with patch.object(approval_routes, "get_db", _get_db):
        yield


@pytest.fixture
def approval_client(approval_db):
    app = FastAPI()
    app.include_router(approval_routes.router)
    with _patch_get_db(approval_db):
        yield TestClient(app, raise_server_exceptions=False)


def _ensure_user(session, username: str) -> int:
    from app.db.models.user import User

    row = session.query(User).filter(User.username == username).first()
    if row is not None:
        return int(row.id)
    user = User(
        username=username,
        password="test-hash",
        display_name=username,
        is_active=True,
    )
    session.add(user)
    session.flush()
    return int(user.id)


def _seed_flow(
    session,
    *,
    flow_key: str = "phase41_flow",
    approver_id: int = 10,
) -> ApprovalFlow:
    flow = ApprovalFlow(
        flow_key=flow_key,
        flow_name="Phase41审批",
        business_type="general",
        is_active=True,
        is_deleted=False,
        allow_withdraw=True,
    )
    node = ApprovalFlowNode(
        node_name="审批节点",
        node_order=1,
        approver_type="user",
        approver_ids=json.dumps([approver_id]),
        is_active=True,
    )
    flow.nodes = [node]
    session.add(flow)
    session.commit()
    session.refresh(flow)
    return flow


# ---------------------------------------------------------------------------
# approval
# ---------------------------------------------------------------------------


def test_approval_withdraw_pending_request(
    approval_client: TestClient,
    approval_db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(approval_routes, "notify_mobile_user", lambda *a, **k: None)
    session = approval_db()
    try:
        applicant_id = _ensure_user(session, "p41_applicant")
        approver_id = _ensure_user(session, "p41_approver")
        _seed_flow(session, flow_key="phase41_withdraw", approver_id=approver_id)
        submit = approval_client.post(
            "/api/approval/requests",
            json={"flow_key": "phase41_withdraw", "title": "撤回单"},
            headers={"X-User-ID": str(applicant_id)},
        )
        assert submit.status_code == 200
        req_id = submit.json()["data"]["id"]
        withdraw = approval_client.post(
            f"/api/approval/requests/{req_id}/withdraw",
            json={},
            headers={"X-User-ID": str(applicant_id)},
        )
        assert withdraw.status_code == 200
        assert withdraw.json()["data"]["status"] == ApprovalStatus.WITHDRAWN.value
    finally:
        session.close()


def test_approval_withdraw_forbidden_for_non_applicant(
    approval_client: TestClient,
    approval_db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(approval_routes, "notify_mobile_user", lambda *a, **k: None)
    session = approval_db()
    try:
        applicant_id = _ensure_user(session, "p41_app2")
        other_id = _ensure_user(session, "p41_other")
        approver_id = _ensure_user(session, "p41_app2_approver")
        _seed_flow(session, flow_key="phase41_forbid", approver_id=approver_id)
        submit = approval_client.post(
            "/api/approval/requests",
            json={"flow_key": "phase41_forbid", "title": "他人撤回"},
            headers={"X-User-ID": str(applicant_id)},
        )
        req_id = submit.json()["data"]["id"]
        withdraw = approval_client.post(
            f"/api/approval/requests/{req_id}/withdraw",
            json={},
            headers={"X-User-ID": str(other_id)},
        )
        assert withdraw.status_code == 403
        assert "申请人" in withdraw.json()["message"]
    finally:
        session.close()


def test_approval_delete_final_request(
    approval_client: TestClient,
    approval_db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(approval_routes, "notify_mobile_user", lambda *a, **k: None)
    session = approval_db()
    try:
        applicant_id = _ensure_user(session, "p41_del_app")
        approver_id = _ensure_user(session, "p41_del_appr")
        _seed_flow(session, flow_key="phase41_delete", approver_id=approver_id)
        submit = approval_client.post(
            "/api/approval/requests",
            json={"flow_key": "phase41_delete", "title": "删除单"},
            headers={"X-User-ID": str(applicant_id)},
        )
        req_id = submit.json()["data"]["id"]
        approval_client.post(
            f"/api/approval/requests/{req_id}/approve",
            json={"opinion": "ok"},
            headers={"X-User-ID": str(approver_id)},
        )
        deleted = approval_client.delete(
            f"/api/approval/requests/{req_id}",
            headers={"X-User-ID": str(applicant_id)},
        )
        assert deleted.status_code == 200
        missing = approval_client.get(f"/api/approval/requests/{req_id}")
        assert missing.status_code == 404
    finally:
        session.close()


def test_approval_flow_detail_not_found(approval_client: TestClient) -> None:
    r = approval_client.get("/api/approval/flows/99999")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# finance
# ---------------------------------------------------------------------------


def test_finance_receivables_query_params(finance_client: TestClient) -> None:
    svc = MagicMock()
    svc.get_receivables.return_value = {"success": True, "data": [], "total": 0}
    with patch("app.application.finance_app_service.FinanceAppService", return_value=svc):
        r = finance_client.get(
            "/api/finance/receivables",
            params={
                "start_date": "2026-01-01",
                "end_date": "2026-06-30",
                "status": "pending",
                "page": 2,
                "per_page": 50,
            },
        )
    assert r.status_code == 200
    kwargs = svc.get_receivables.call_args.kwargs
    assert kwargs["status"] == "pending"
    assert kwargs["page"] == 2


def test_finance_payables_with_dates(finance_client: TestClient) -> None:
    svc = MagicMock()
    svc.get_payables.return_value = {"success": True, "data": [{"outstanding": 10}]}
    with patch("app.application.finance_app_service.FinanceAppService", return_value=svc):
        r = finance_client.get(
            "/api/finance/payables",
            params={"start_date": "2026-05-01", "status": "open"},
        )
    assert r.status_code == 200
    assert svc.get_payables.call_args.kwargs["start_date"].month == 5


def test_finance_transaction_get_not_found(finance_client: TestClient) -> None:
    svc = MagicMock()
    svc.get_transaction.return_value = {"success": False, "message": "凭证不存在"}
    with patch("app.application.finance_app_service.FinanceAppService", return_value=svc):
        r = finance_client.get("/api/finance/transactions/404")
    assert r.status_code == 200
    assert r.json()["success"] is False


# ---------------------------------------------------------------------------
# shipment
# ---------------------------------------------------------------------------


def test_shipment_generate_validation_errors(shipment_client: TestClient) -> None:
    empty_unit = shipment_client.post("/api/shipment/generate", json={"products": [{"x": 1}]})
    assert empty_unit.status_code == 400
    empty_products = shipment_client.post(
        "/api/shipment/generate",
        json={"unit_name": "甲公司"},
    )
    assert empty_products.status_code == 400


def test_shipment_generate_service_failure(
    shipment_client: TestClient, mock_shipment_svc: MagicMock
) -> None:
    mock_shipment_svc.generate_shipment_document.return_value = {
        "success": False,
        "message": "生成失败",
    }
    r = shipment_client.post(
        "/api/shipment/generate",
        json={"unit_name": "甲公司", "products": [{"name": "漆"}]},
    )
    assert r.status_code == 500
    assert r.json()["success"] is False


def test_shipment_generate_success(
    shipment_client: TestClient, mock_shipment_svc: MagicMock
) -> None:
    r = shipment_client.post(
        "/api/shipment/generate",
        json={"unit_name": "甲公司", "products": [{"model_number": "9803"}]},
    )
    assert r.status_code == 200
    assert r.json()["file_path"] == "/tmp/p41.xlsx"
    mock_shipment_svc.generate_shipment_document.assert_called_once()


def test_shipment_orders_latest_alias(
    shipment_client: TestClient, mock_shipment_svc: MagicMock
) -> None:
    r = shipment_client.get("/api/shipment/orders/latest")
    assert r.status_code == 200
    mock_shipment_svc.get_orders.assert_called_once_with(limit=10)


# ---------------------------------------------------------------------------
# customer (xcagi_compat)
# ---------------------------------------------------------------------------


def test_compat_customer_get_not_found(compat_customer_client: TestClient) -> None:
    with (
        patch(
            "app.mod_sdk.erp_customers_facade.is_erp_customers_via_service_enabled",
            return_value=False,
        ),
        patch.object(customer_routes, "_customer_find_by_id", return_value=None),
    ):
        r = compat_customer_client.get("/customers/404")
    assert r.status_code == 404


def test_compat_customer_update_via_service(compat_customer_client: TestClient) -> None:
    with (
        patch(
            "app.mod_sdk.erp_customers_facade.is_erp_customers_via_service_enabled",
            return_value=True,
        ),
        patch(
            "app.mod_sdk.erp_customers_facade.customers_update",
            return_value={"success": True, "data": {"id": 2, "unit_name": "乙公司"}},
        ) as upd,
    ):
        r = compat_customer_client.put(
            "/customers/2",
            json={"unit_name": "乙公司"},
        )
    assert r.status_code == 200
    upd.assert_called_once()


def test_compat_customer_export_not_implemented() -> None:
    from fastapi import HTTPException

    from app.fastapi_routes.domains.customer.routes import customers_export_stub

    with pytest.raises(HTTPException) as exc:
        customers_export_stub()
    assert exc.value.status_code == 501
    assert "尚未" in str(exc.value.detail)


# ---------------------------------------------------------------------------
# tools
# ---------------------------------------------------------------------------


def test_legacy_tools_execute_route(tools_client: TestClient) -> None:
    with patch(
        "app.routes.tools.run_archive_tools_execute",
        return_value=({"success": True, "tool": "excel_analysis"}, 200),
    ):
        r = tools_client.post(
            "/api/tools/execute",
            json={"tool_id": "excel_analysis", "params": {}},
        )
    assert r.status_code == 200
    assert r.json()["tool"] == "excel_analysis"


def test_compat_tools_list_role_filter(tools_client: TestClient) -> None:
    payload = {
        "tools": [
            {"id": "a", "roles": ["admin"]},
            {"id": "b", "roles": []},
            {"id": "c", "roles": ["viewer"]},
        ],
    }
    with patch(
        "app.fastapi_routes.domains.misc.routes.get_tools_payload",
        return_value=payload,
    ):
        r = tools_client.get("/tools", params={"role": "admin"})
    assert r.status_code == 200
    ids = [t["id"] for t in r.json()["tools"]]
    assert ids == ["a", "b"]


def test_compat_tool_categories_list(tools_client: TestClient) -> None:
    with patch(
        "app.fastapi_routes.domains.misc.routes.get_tool_categories_payload",
        return_value={"categories": [{"id": "erp", "label": "ERP"}]},
    ):
        r = tools_client.get("/tool-categories/")
    assert r.status_code == 200
    assert r.json()["categories"][0]["id"] == "erp"
