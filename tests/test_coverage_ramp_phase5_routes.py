"""COVERAGE_RAMP Phase 5: FastAPI routes (print, xcmax_admin, legacy helpers, misc)."""

from __future__ import annotations

import json
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.fastapi_routes import debug_client_log as debug_routes
from app.fastapi_routes import fhd_meta as fhd_meta_routes
from app.fastapi_routes import health_k8s as health_routes
from app.fastapi_routes import neuro_migration_routes as neuro_routes
from app.fastapi_routes import print_routes, spa_fallback
from app.fastapi_routes import state as state_routes
from app.fastapi_routes import xcmax_admin as xcmax_routes
from app.fastapi_routes.domains.misc import helpers as legacy_helpers

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_printer_service() -> MagicMock:
    svc = MagicMock()
    svc.get_printers.return_value = {
        "success": True,
        "printers": [{"name": "DocPrinter"}, {"name": "LabelPrinter"}],
    }
    svc.get_printer_selection.return_value = {
        "document_printer": "DocPrinter",
        "label_printer": "LabelPrinter",
    }
    svc.save_printer_selection.return_value = {"success": True}
    svc.classify_printers.return_value = {"document": ["DocPrinter"], "label": ["LabelPrinter"]}
    svc.get_default_printer.return_value = {"success": True, "printer": "DocPrinter"}
    svc.print_document.return_value = {"success": True}
    svc.print_label.return_value = {"success": True, "status": "printed"}
    svc.test_printer.return_value = {"success": True}
    svc.validate_printer_separation.return_value = {"valid": True}
    svc.get_document_printer.return_value = "DocPrinter"
    svc.get_label_printer.return_value = "LabelPrinter"
    return svc


@pytest.fixture
def print_client(mock_printer_service: MagicMock, monkeypatch: pytest.MonkeyPatch):
    print_routes._print_confirm_cache.clear()

    def _svc():
        return mock_printer_service

    monkeypatch.setattr(print_routes, "_svc", _svc)
    app = FastAPI()
    app.include_router(print_routes.router)
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def xcmax_client(monkeypatch: pytest.MonkeyPatch):
    app = FastAPI()
    app.include_router(xcmax_routes.router)
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def admin_session_ok(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(xcmax_routes, "_require_market_admin_session", lambda request: None)

    async def _proxy(request, method, path, *, json_body=None, **kwargs):
        if path.endswith("/health"):
            return {
                "ok": True,
                "staffing": {"missing_employees": []},
                "change_requests": {"pending": 0},
            }
        return {"success": True, "data": []}

    monkeypatch.setattr(xcmax_routes, "_market_admin_proxy", _proxy)


# ---------------------------------------------------------------------------
# print_routes — unit helpers
# ---------------------------------------------------------------------------


def test_print_confirm_cache_ttl() -> None:
    print_routes._print_confirm_cache.clear()
    token = print_routes._create_print_confirm_token({"file_path": "/tmp/a.pdf"})
    assert token in print_routes._print_confirm_cache
    print_routes._print_confirm_cache[token]["expires_at"] = time.time() - 1
    print_routes._cleanup_print_confirm_cache()
    assert token not in print_routes._print_confirm_cache


def test_print_consume_confirm_token() -> None:
    print_routes._print_confirm_cache.clear()
    token = print_routes._create_print_confirm_token({"copies": 2})
    payload = print_routes._consume_print_confirm_token(token)
    assert payload.get("copies") == 2
    assert print_routes._consume_print_confirm_token(token) == {}


# ---------------------------------------------------------------------------
# print_routes — HTTP
# ---------------------------------------------------------------------------


def test_print_get_printers(print_client, mock_printer_service: MagicMock) -> None:
    r = print_client.get("/api/print/printers")
    assert r.status_code == 200
    mock_printer_service.get_printers.assert_called_once()


def test_print_get_printers_error(print_client, mock_printer_service: MagicMock) -> None:
    mock_printer_service.get_printers.side_effect = RuntimeError("boom")
    r = print_client.get("/api/print/printers")
    assert r.status_code == 500
    assert r.json()["success"] is False


def test_print_printer_selection_get_put(print_client, mock_printer_service: MagicMock) -> None:
    r = print_client.get("/api/print/printer-selection")
    assert r.status_code == 200
    r2 = print_client.put(
        "/api/print/printer-selection",
        json={"document_printer": "DocPrinter", "label_printer": "LabelPrinter"},
    )
    assert r2.status_code == 200


def test_print_printer_selection_invalid_name(print_client) -> None:
    r = print_client.put(
        "/api/print/printer-selection",
        json={"document_printer": "UnknownPrinter"},
    )
    assert r.status_code == 400


def test_print_default_and_test_endpoints(print_client) -> None:
    assert print_client.get("/api/print/default").status_code == 200
    assert print_client.get("/api/print/test").status_code == 200
    assert print_client.get("/api/print/validate").status_code == 200
    assert print_client.get("/api/print/document-printer").status_code == 200
    assert print_client.get("/api/print/label-printer").status_code == 200


def test_print_document_validation(print_client, tmp_path) -> None:
    r = print_client.post("/api/print/document", json={})
    assert r.status_code == 400
    missing = print_client.post(
        "/api/print/document", json={"file_path": str(tmp_path / "nope.pdf")}
    )
    assert missing.status_code == 400
    doc = tmp_path / "doc.pdf"
    doc.write_bytes(b"%PDF")
    ok = print_client.post("/api/print/document", json={"file_path": str(doc)})
    assert ok.status_code == 200


def test_print_label_confirm_flow(print_client, tmp_path) -> None:
    label = tmp_path / "label.png"
    label.write_bytes(b"\x89PNG\r\n")
    path = str(label)
    step1 = print_client.post(
        "/api/print/label",
        json={"file_path": path, "copies": 2, "require_confirm": True},
    )
    assert step1.status_code == 200
    body = step1.json()
    assert body.get("status") == "print_confirm_required"
    token = body["confirm_token"]
    step2 = print_client.post(
        "/api/print/label",
        json={"file_path": path, "confirm_token": token, "require_confirm": True},
    )
    assert step2.status_code == 200


def test_print_label_cancel_and_bad_copies(print_client, tmp_path) -> None:
    label = tmp_path / "l.png"
    label.write_bytes(b"x")
    path = str(label)
    cancel = print_client.post(
        "/api/print/label",
        json={
            "file_path": path,
            "require_confirm": True,
            "confirm_action": "cancel",
            "confirm_token": "t",
        },
    )
    assert cancel.json().get("status") == "print_cancelled"
    bad = print_client.post("/api/print/label", json={"file_path": path, "copies": 0})
    assert bad.status_code == 400


def test_print_test_printer_post(print_client) -> None:
    assert print_client.post("/api/print/test", json={}).status_code == 400
    assert (
        print_client.post("/api/print/test", json={"printer_name": "DocPrinter"}).status_code == 200
    )


def test_print_workflow_dispatch(print_client, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    fake_print_app = MagicMock()
    fake_print_app.print_single_label.return_value = {"success": True}
    monkeypatch.setattr(
        "app.application.print_app_service.get_print_application_service",
        lambda: fake_print_app,
    )
    monkeypatch.setattr(
        "app.application.get_product_app_service",
        lambda: MagicMock(search_products=MagicMock(return_value=[])),
    )
    r = print_client.post(
        "/api/print/workflow/label-print/dispatch",
        json={"model_number": "M-1", "quantity": 2, "idempotency_key": "idem-1"},
    )
    assert r.status_code == 200
    r2 = print_client.post(
        "/api/print/workflow/label-print/dispatch",
        json={"model_number": "M-1", "idempotency_key": "idem-1"},
    )
    assert r2.json().get("skipped") is True
    assert print_client.post("/api/print/workflow/label-print/dispatch", json={}).status_code == 400


def test_print_list_labels_and_serve(
    print_client, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    labels_dir = tmp_path / "labels"
    labels_dir.mkdir()
    (labels_dir / "ORD_第1项.png").write_bytes(b"\x89PNG")
    monkeypatch.setattr(
        "app.utils.path_utils.get_resource_path",
        lambda *parts: str(labels_dir) if parts[-1] == "商标导出" else str(tmp_path),
    )
    listed = print_client.get("/api/print/list_labels", params={"limit": 5})
    assert listed.status_code == 200
    assert listed.json()["success"] is True
    fname = listed.json()["labels"][0]["filename"]
    served = print_client.get(f"/api/print/label/{fname}")
    assert served.status_code == 200


# ---------------------------------------------------------------------------
# xcmax_admin — unit + HTTP
# ---------------------------------------------------------------------------


def test_xcmax_inject_digest_api_base() -> None:
    out = xcmax_routes._inject_digest_api_base({"data": {"code": "x"}}, "http://m.test")
    assert out["data"]["digest_api_base"] == "http://m.test"


def test_xcmax_collect_mod_modules_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.infrastructure.mods.mod_manager.get_mod_manager",
        lambda: None,
    )
    assert xcmax_routes._collect_mod_modules() == []


def test_xcmax_probe_remote_health_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Resp:
        def read(self, n: int) -> bytes:
            return json.dumps({"version": "9.0"}).encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: _Resp())
    out = xcmax_routes._probe_remote_health_sync()
    assert out["data"]["reachable"] is True


def test_xcmax_probe_remote_health_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: (_ for _ in ()).throw(OSError("down")),
    )
    out = xcmax_routes._probe_remote_health_sync()
    assert out["data"]["reachable"] is False


def test_xcmax_list_modules(xcmax_client) -> None:
    r = xcmax_client.get("/api/xcmax/admin/modules")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["total"] >= len(xcmax_routes.CORE_MODULES)


@pytest.mark.asyncio
async def test_xcmax_remote_status(xcmax_client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        xcmax_routes,
        "_probe_remote_health_sync",
        lambda: {"success": True, "data": {"reachable": True}},
    )
    r = xcmax_client.get("/api/xcmax/admin/remote-status")
    assert r.status_code == 200


def test_xcmax_sync_status_fallback(xcmax_client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.db.xcmax_sync.SyncDb",
        lambda: (_ for _ in ()).throw(RuntimeError("no db")),
    )
    r = xcmax_client.get("/api/xcmax/sync/status")
    assert r.status_code == 200
    assert r.json()["data"]["healthy"] is False


def test_xcmax_sync_changes_empty(xcmax_client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.db.xcmax_sync.SyncDb",
        lambda: (_ for _ in ()).throw(RuntimeError("no db")),
    )
    r = xcmax_client.get("/api/xcmax/sync/changes")
    assert r.status_code == 200
    assert r.json()["count"] == 0


def test_xcmax_sync_push_fail(xcmax_client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.application.xcmax_sync_app.push_outbox",
        lambda **kw: (_ for _ in ()).throw(RuntimeError("push fail")),
    )
    r = xcmax_client.post("/api/xcmax/sync/push")
    assert r.status_code == 500


def test_xcmax_require_admin_session_unauthorized(
    xcmax_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.application.session_account_meta.load_session_account_meta",
        lambda sid: None,
    )
    monkeypatch.setattr(
        "app.fastapi_routes.domains.misc.helpers._session_id_from_request",
        lambda request: None,
    )
    gate = xcmax_routes._require_market_admin_session(SimpleNamespace(headers={}, cookies={}))
    assert gate is not None
    assert gate.status_code == 401


def test_xcmax_wechat_groups_forbidden(xcmax_client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        xcmax_routes,
        "_require_market_admin_session",
        lambda request: xcmax_routes.JSONResponse({"success": False}, status_code=403),
    )
    r = xcmax_client.get("/api/xcmax/admin/wechat/groups")
    assert r.status_code == 403


def test_xcmax_wechat_groups_ok(xcmax_client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(xcmax_routes, "_require_market_admin_session", lambda request: None)
    monkeypatch.setattr(
        "app.services.wechat_group_customer_bridge.list_group_contacts",
        lambda **kw: [{"id": 1}],
    )
    r = xcmax_client.get("/api/xcmax/admin/wechat/groups")
    assert r.status_code == 200
    assert r.json()["total"] == 1


def test_xcmax_digest_identity_404_fallback(xcmax_client, monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.responses import JSONResponse

    async def _proxy(*args, **kwargs):
        return JSONResponse({"success": False}, status_code=404)

    monkeypatch.setattr(xcmax_routes, "_market_admin_proxy", _proxy)
    monkeypatch.setattr(
        "app.fastapi_routes.market_account._market_base_url",
        lambda: "http://market.test",
    )
    r = xcmax_client.get("/api/xcmax/admin/digest-identity")
    assert r.status_code == 200
    assert r.json()["success"] is True


def test_xcmax_all_hands_session_bad_id(xcmax_client, admin_session_ok) -> None:
    r = xcmax_client.get("/api/xcmax/admin/all-hands-report/sessions/!!!")
    assert r.status_code == 400


def test_xcmax_ops_job_bad_id(xcmax_client, admin_session_ok) -> None:
    r = xcmax_client.get("/api/xcmax/ops/jobs/!!!")
    assert r.status_code == 400


def test_xcmax_ops_duty_run_bad_id(xcmax_client, admin_session_ok) -> None:
    r = xcmax_client.get("/api/xcmax/ops/duty-runs/0")
    assert r.status_code == 400


def test_xcmax_ops_staffing_install_local_missing_id(xcmax_client, admin_session_ok) -> None:
    r = xcmax_client.post("/api/xcmax/ops/staffing/install-local", json={})
    assert r.status_code == 400


def test_xcmax_ops_closure_status(xcmax_client, admin_session_ok) -> None:
    r = xcmax_client.get("/api/xcmax/ops/closure-status")
    assert r.status_code == 200
    assert "deliverable" in r.json()["data"]


def test_xcmax_ops_dispatch_desktop_source(
    xcmax_client, admin_session_ok, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict = {}

    async def _proxy(request, method, path, *, json_body=None, **kwargs):
        captured["body"] = json_body
        return {"ok": True}

    monkeypatch.setattr(xcmax_routes, "_market_admin_proxy", _proxy)
    r = xcmax_client.post("/api/xcmax/ops/dispatch", json={"task_description": "t"})
    assert r.status_code == 200
    assert captured["body"]["dispatch_source"] == "desktop"


def test_xcmax_sync_conflicts_list(xcmax_client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.admin_sync_service.list_sync_conflicts",
        lambda limit=50: [{"inbox_id": 1}],
    )
    r = xcmax_client.get("/api/xcmax/sync/conflicts")
    assert r.status_code == 200
    assert r.json()["count"] == 1


def test_xcmax_sync_resolve_skip(xcmax_client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.admin_sync_service.mark_inbox_skipped",
        lambda inbox_id: None,
    )
    mock_db = MagicMock()
    monkeypatch.setattr("app.db.xcmax_sync.SyncDb", lambda: mock_db)
    r = xcmax_client.post("/api/xcmax/sync/conflicts/9/resolve", json={"action": "skip"})
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# legacy_helpers — unit
# ---------------------------------------------------------------------------


def test_legacy_http_exception_to_json() -> None:
    exc = HTTPException(status_code=400, detail={"message": "bad"})
    resp = legacy_helpers._http_exception_to_json(exc)
    assert resp.status_code == 400


def test_legacy_session_and_message_to_dict() -> None:
    sess = legacy_helpers._session_to_dict(
        {"session_id": "s1", "user_id": 2, "title": "t", "message_count": 1}
    )
    assert sess["session_id"] == "s1"
    msg = legacy_helpers._message_to_dict(("id", "sid", 1, "user", "hi", "intent", "meta", "ts"))
    assert msg["content"] == "hi"


def test_legacy_require_login_and_permission(monkeypatch: pytest.MonkeyPatch) -> None:
    request = SimpleNamespace(headers={}, cookies={})
    monkeypatch.setattr(
        "app.infrastructure.auth.dependencies.resolve_session_user",
        lambda req: None,
    )
    monkeypatch.setattr(
        "app.infrastructure.auth.dependencies.get_logged_in_user",
        lambda req: (_ for _ in ()).throw(HTTPException(status_code=401, detail="login")),
    )
    user, err = legacy_helpers._require_login_user(request)
    assert user is None
    assert err is not None

    monkeypatch.setattr(
        "app.fastapi_routes.domains.misc.helpers.resolve_session_user",
        lambda req: {"id": 1},
    )
    auth = MagicMock()
    auth.has_permission.return_value = False
    monkeypatch.setattr(
        "app.application.facades.session_facade.get_auth_service",
        lambda: auth,
    )
    user2, err2 = legacy_helpers._require_permission(request, "erp.read")
    assert user2 is None
    assert err2.status_code == 403


# ---------------------------------------------------------------------------
# fhd_meta, debug, state, spa, health, neuro
# ---------------------------------------------------------------------------


@pytest.fixture
def fhd_meta_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("FHD_DB_READ_TOKEN", raising=False)
    monkeypatch.delenv("FHD_DB_WRITE_TOKEN", raising=False)
    app = FastAPI()
    app.include_router(fhd_meta_routes.router)
    return TestClient(app)


def test_fhd_meta_db_tokens_status(fhd_meta_client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FHD_DB_READ_TOKEN", "r")
    monkeypatch.setenv("FHD_DB_WRITE_TOKEN", "w")
    r = fhd_meta_client.get("/api/fhd/db-tokens/status")
    assert r.status_code == 200
    assert r.json()["read_token_configured"] is True


@pytest.fixture
def debug_client():
    app = FastAPI()
    app.include_router(debug_routes.router)
    return TestClient(app)


def test_debug_client_log_ok(debug_client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.utils.logging_utils.ingest_client_debug_json",
        lambda body: {"success": True, "ingested": True},
    )
    r = debug_client.post("/api/debug/client-log", json={"level": "info", "msg": "x"})
    assert r.status_code == 200
    assert r.json()["success"] is True


def test_debug_client_log_error(debug_client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.utils.logging_utils.ingest_client_debug_json",
        lambda body: (_ for _ in ()).throw(RuntimeError("fail")),
    )
    r = debug_client.post("/api/debug/client-log", json={})
    assert r.json()["success"] is False


@pytest.fixture
def state_client(tmp_path, monkeypatch: pytest.MonkeyPatch):
    state_file = tmp_path / "state.json"
    monkeypatch.setattr(state_routes, "STATE_FILE", state_file)
    app = FastAPI()
    app.include_router(state_routes.router)
    return TestClient(app)


def test_state_client_mods_off_roundtrip(state_client) -> None:
    r = state_client.get("/api/state/client-mods-off")
    assert r.status_code == 200
    assert r.json()["data"]["client_mods_off"] is False
    r2 = state_client.post("/api/state/client-mods-off", json={"client_mods_off": True})
    assert r2.status_code == 200
    r3 = state_client.get("/api/state/client-mods-off")
    assert r3.json()["data"]["client_mods_off"] is True


def test_spa_fallback_helpers(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    vue = tmp_path / "vue-dist"
    vue.mkdir()
    (vue / "sw.js").write_text("//sw")
    monkeypatch.setattr(spa_fallback, "_vue_dist_dir", lambda: str(vue))
    resp = spa_fallback._try_serve_vue_dist_root_file("sw.js")
    assert resp is not None
    assert spa_fallback._try_serve_vue_dist_root_file("missing.js") is None


def test_spa_register_fallback(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    vue = tmp_path / "vue-dist"
    vue.mkdir()
    (vue / "index.html").write_text("<html></html>")
    monkeypatch.setattr(spa_fallback, "_vue_dist_dir", lambda: str(vue))
    monkeypatch.setattr(
        "app.utils.path_utils.get_base_dir",
        lambda: str(tmp_path),
    )
    app = FastAPI()
    spa_fallback.register_spa_history_fallback(app)
    client = TestClient(app)
    assert client.get("/some-vue-route").status_code == 200
    assert client.get("/api/unknown").status_code == 404


def test_health_k8s_liveness_and_readiness(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health_routes, "_check_database", lambda: {"status": "healthy"})
    monkeypatch.setattr(health_routes, "_check_redis", lambda: {"status": "healthy"})
    monkeypatch.setattr(health_routes, "_check_ai_service", lambda: {"status": "healthy"})
    monkeypatch.setattr(health_routes, "_check_pgvector", lambda: {"status": "disabled"})
    monkeypatch.setattr(health_routes, "_check_rasa_nlu", lambda: {"status": "disabled"})
    app = FastAPI()
    app.include_router(health_routes.router)
    client = TestClient(app)
    assert client.get("/health/liveness").status_code == 200
    assert client.get("/health/readiness").status_code == 200
    assert client.get("/health/details").status_code == 200
    assert client.get("/api/diagnostics/capabilities").status_code == 200


def test_neuro_migration_smoke_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.neuro_bus.integrations.intent_integration.is_neuro_stack_enabled",
        lambda: False,
    )
    app = FastAPI()
    app.include_router(neuro_routes.router)
    r = TestClient(app).get("/api/neuro/migration-smoke")
    assert r.status_code == 200
    assert r.json()["neuro_stack_enabled"] is False
