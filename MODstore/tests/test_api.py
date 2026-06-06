"""MODstore HTTP API 集成测试（TestClient）。"""

from __future__ import annotations

import io
import json
import zipfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_openapi_schema(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    assert spec["info"]["title"] == "MODstore"
    paths = spec.get("paths", {})
    assert "/api/mods" in paths
    assert "/api/debug/sandbox" in paths
    assert "/api/mods/{mod_id}/workflow-employees/scaffold" in paths
    assert "/api/mods/{mod_id}/employee-sandbox/run" in paths
    assert "/api/portal/fetch-wallet-secret" in paths


def test_config_get_default_portal_plans_url(client):
    r = client.get("/api/config")
    assert r.status_code == 200
    j = r.json()
    assert "portal_plans_url" in j
    assert "xiu-ci.com" in j["portal_plans_url"]


def test_put_config_portal_urls(client, library: Path):
    r = client.put(
        "/api/config",
        json={
            "library_root": str(library),
            "xcagi_root": "",
            "xcagi_backend_url": "http://test.invalid",
            "portal_plans_url": "https://staging.example/market/plans",
            "portal_wallet_sync_url": "https://api.example/v1/me/wallet-secret",
        },
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["saved_portal_plans_url"] == "https://staging.example/market/plans"
    assert j["portal_plans_url"] == "https://staging.example/market/plans"
    assert j["saved_portal_wallet_sync_url"] == "https://api.example/v1/me/wallet-secret"


def test_portal_fetch_wallet_secret_requires_sync(client):
    r = client.post(
        "/api/portal/fetch-wallet-secret",
        json={"sync_url": "", "authorization": "Bearer xxxxxxxx"},
    )
    assert r.status_code == 400


def test_portal_fetch_wallet_secret_ok(client, library: Path, monkeypatch):
    r0 = client.put(
        "/api/config",
        json={
            "library_root": str(library),
            "xcagi_root": "",
            "xcagi_backend_url": "http://test.invalid",
            "portal_plans_url": "",
            "portal_wallet_sync_url": "https://sync.example.com/wallet",
        },
    )
    assert r0.status_code == 200, r0.text

    def fake_fetch(sync_url: str, authorization: str):
        assert "sync.example.com" in sync_url
        assert "Bearer" in authorization
        return {"ok": True, "wallet_secret": "from-portal"}

    monkeypatch.setattr("modstore_server.fhd_routes_api.fetch_wallet_secret", fake_fetch)
    r = client.post(
        "/api/portal/fetch-wallet-secret",
        json={"sync_url": "", "authorization": "Bearer xxxxxxxx"},
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True, "wallet_secret": "from-portal"}


def test_create_list_get_mod(client, library: Path):
    r = client.post(
        "/api/mods/create",
        json={"mod_id": "api-test-mod", "display_name": "API Test"},
    )
    assert r.status_code == 200, r.text
    assert (library / "api-test-mod" / "manifest.json").is_file()

    r = client.get("/api/mods")
    assert r.status_code == 200
    ids = [row["id"] for row in r.json()["data"]]
    assert "api-test-mod" in ids

    r = client.get("/api/mods/api-test-mod")
    assert r.status_code == 200
    assert r.json()["id"] == "api-test-mod"


def test_mod_file_get_put(client, library: Path):
    client.post(
        "/api/mods/create",
        json={"mod_id": "file-mod", "display_name": "F"},
    )
    r = client.put(
        "/api/mods/file-mod/file",
        json={"path": "notes.md", "content": "# hi\n"},
    )
    assert r.status_code == 200, r.text
    assert (library / "file-mod" / "notes.md").read_text(encoding="utf-8") == "# hi\n"

    r = client.get("/api/mods/file-mod/file", params={"path": "notes.md"})
    assert r.status_code == 200
    assert r.json()["content"] == "# hi\n"


def test_debug_sandbox_copy(client, library: Path, project_home: Path):
    client.post(
        "/api/mods/create",
        json={"mod_id": "sand-mod", "display_name": "S"},
    )
    r = client.post(
        "/api/debug/sandbox",
        json={"mod_id": "sand-mod", "mode": "copy"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    root = Path(data["mods_root"])
    assert root.is_dir()
    assert root.parent.parent.parent == project_home
    assert (root / "sand-mod" / "manifest.json").is_file()


def test_focus_primary(client, library: Path):
    client.post("/api/mods/create", json={"mod_id": "p-a", "display_name": "A"})
    client.post("/api/mods/create", json={"mod_id": "p-b", "display_name": "B"})
    r = client.post("/api/debug/focus-primary", json={"mod_id": "p-b"})
    assert r.status_code == 200, r.text
    ma = json.loads((library / "p-a" / "manifest.json").read_text(encoding="utf-8"))
    mb = json.loads((library / "p-b" / "manifest.json").read_text(encoding="utf-8"))
    assert ma.get("primary") is False
    assert mb.get("primary") is True


def test_import_zip(client, library: Path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        manifest = {
            "id": "zip-mod",
            "name": "Z",
            "version": "1.0.0",
            "backend": {"entry": "blueprints", "init": "mod_init"},
            "frontend": {"routes": "frontend/routes.js"},
        }
        zf.writestr(
            "zip-mod/manifest.json",
            json.dumps(manifest, ensure_ascii=False),
        )
        zf.writestr("zip-mod/readme.md", "x")
    buf.seek(0)
    r = client.post(
        "/api/mods/import",
        files={"file": ("z.zip", buf.getvalue(), "application/zip")},
    )
    assert r.status_code == 200, r.text
    assert (library / "zip-mod" / "manifest.json").is_file()


def test_sync_push_pull(tmp_path, monkeypatch):
    """使用真实目录结构验证 deploy / pull。"""
    library = tmp_path / "lib"
    library.mkdir()
    xcagi = tmp_path / "xcagi"
    (xcagi / "mods").mkdir(parents=True)

    from modman.repo_config import RepoConfig
    from modstore_server.app import app
    from fastapi.testclient import TestClient

    cfg = RepoConfig(library_root=str(library), xcagi_root=str(xcagi))

    monkeypatch.setattr("modstore_server.app.load_config", lambda: cfg)
    monkeypatch.setattr("modstore_server.app.save_config", lambda c: None)
    monkeypatch.setattr("modstore_server.app.project_root", lambda: tmp_path / "ph")
    monkeypatch.setattr("modman.repo_config.load_config", lambda: cfg)
    monkeypatch.setattr("modman.repo_config.save_config", lambda c: None)
    monkeypatch.setattr("modman.store.project_root", lambda: tmp_path / "ph")
    monkeypatch.setattr("modstore_server.fhd_routes_api.load_config", lambda: cfg)
    monkeypatch.setattr("modstore_server.fhd_routes_api.save_config", lambda c: None)
    monkeypatch.setattr("modstore_server.fhd_routes_api.project_root", lambda: tmp_path / "ph")
    monkeypatch.setattr("modstore_server.fhd_modstore_state.load_config", lambda: cfg)

    c = TestClient(app)
    r = c.post("/api/mods/create", json={"mod_id": "sync-m", "display_name": "S"})
    assert r.status_code == 200

    r = c.post("/api/sync/push", json={"mod_ids": ["sync-m"]})
    assert r.status_code == 200
    assert (xcagi / "mods" / "sync-m" / "manifest.json").is_file()

    shutil.rmtree(library / "sync-m", ignore_errors=True)
    r = c.post("/api/sync/pull", json={"mod_ids": ["sync-m"]})
    assert r.status_code == 200
    assert (library / "sync-m" / "manifest.json").is_file()


@patch("modstore_server.app.httpx.Client")
def test_xcagi_loading_status_mocked(mock_client_cls, client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"success": True, "data": {"mods_loaded": 0}}
    inst = MagicMock()
    inst.__enter__.return_value.get.return_value = mock_resp
    mock_client_cls.return_value = inst

    r = client.get("/api/xcagi/loading-status")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["data"]["success"] is True


def test_employee_sandbox_run_skips_without_employees(client, library: Path):
    client.post("/api/mods/create", json={"mod_id": "sb-empty", "display_name": "S"})
    r = client.post("/api/mods/sb-empty/employee-sandbox/run", json={"probe_http": False})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("ok") is True
    assert body.get("static", {}).get("skipped") is True


def test_workflow_employee_scaffold(client, library: Path, monkeypatch):
    monkeypatch.setenv("MODSTORE_SCAFFOLD_AUTO_MERGE_BLUEPRINTS", "1")
    client.post("/api/mods/create", json={"mod_id": "scaf-mod", "display_name": "S"})
    r = client.post(
        "/api/mods/scaf-mod/workflow-employees/scaffold",
        json={
            "id": "helper_one",
            "label": "Helper",
            "panel_title": "T",
            "panel_summary": "S",
            "template": "skeleton_router",
            "force_auto_merge": True,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("ok") is True
    assert any("employee_stubs" in str(p) for p in (body.get("files_written") or []))
    m = json.loads((library / "scaf-mod" / "manifest.json").read_text(encoding="utf-8"))
    wf = m.get("workflow_employees") or []
    assert any(isinstance(x, dict) and x.get("id") == "helper_one" for x in wf)
    assert (library / "scaf-mod" / "backend" / "employee_stubs").is_dir()
    bp = (library / "scaf-mod" / "backend" / "blueprints.py").read_text(encoding="utf-8")
    assert "mount_employee_router" in bp

    r2 = client.post(
        "/api/mods/scaf-mod/workflow-employees/scaffold",
        json={
            "id": "helper_one",
            "label": "Dup",
            "template": "skeleton_router",
            "force_auto_merge": False,
        },
    )
    assert r2.status_code == 400


def test_delete_mod(client):
    client.post("/api/mods/create", json={"mod_id": "del-me", "display_name": "D"})
    r = client.delete("/api/mods/del-me")
    assert r.status_code == 200
    r = client.get("/api/mods/del-me")
    assert r.status_code == 404
