"""xcagi_shell 聚合路由（mods + traditional）契约测试；不依赖 backend/tests/conftest 与 PG。"""

from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers.xcagi_shell import router as xcagi_shell_router
from backend.shell.mods_catalog import list_mod_items


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(xcagi_shell_router, prefix="/api")
    return TestClient(app)


def test_mods_list_shape(monkeypatch, tmp_path):
    """无磁盘 manifest 干扰：仅 fhd_shell_mods.json 目录项 + 内置尾部。"""
    monkeypatch.setattr("backend.shell.mods_catalog.read_manifest_dicts", lambda: [])
    p = tmp_path / "mods.json"
    p.write_text(
        json.dumps(
            [
                {"id": "all", "name": "全部", "type": "category", "color": None},
                {"id": "t_test", "name": "Test", "type": "template", "color": "green"},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("FHD_SHELL_MODS_JSON", str(p))
    r = _client().get("/api/mods/")
    assert r.status_code == 200
    payload = r.json()
    assert payload["success"] is True
    data = payload["data"]
    assert isinstance(data, list) and data[0]["id"] == "all"
    assert data[1]["id"] == "t_test"


def test_list_mod_items_invalid_json_fallback(monkeypatch, tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{ not json", encoding="utf-8")
    monkeypatch.setenv("FHD_SHELL_MODS_JSON", str(p))
    items = list_mod_items()
    assert any(i.id == "出货明细表" for i in items)


def test_list_mod_items_from_env_json(monkeypatch, tmp_path):
    monkeypatch.setattr("backend.shell.mods_catalog.read_manifest_dicts", lambda: [])
    p = tmp_path / "mods.json"
    p.write_text(
        json.dumps(
            [
                {"id": "all", "name": "全部", "type": "category", "color": None},
                {"id": "from_file", "name": "From File", "type": "template", "color": "green"},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("FHD_SHELL_MODS_JSON", str(p))
    items = list_mod_items()
    assert [i.id for i in items] == ["all", "from_file"]


def test_mods_loading_status_and_routes(monkeypatch):
    monkeypatch.setattr("backend.shell.xcagi_mods_discover.read_manifest_dicts", lambda: [])
    c = _client()
    ls = c.get("/api/mods/loading-status")
    assert ls.status_code == 200
    j = ls.json()
    assert j["success"] is True and j["loaded"] is True
    assert j["data"]["status"] == "ready"
    rt = c.get("/api/mods/routes")
    assert rt.json() == {"success": True, "data": []}


def test_startup_status_has_mods_component():
    r = _client().get("/api/startup/status")
    assert r.status_code == 200
    body = r.json()
    assert body["ready"] is True and body["progress_percent"] == 100
    comps = body["components"]
    assert any(c["name"] == "mods" and c["status"] == "ready" for c in comps)


def test_mod_agent_status_placeholder():
    r = _client().get("/api/mods/proj1/phone-agent/status")
    assert r.status_code == 200
    d = r.json()
    assert d["success"] is True
    inner = d["data"]
    assert inner["project_id"] == "proj1"
    assert inner["agent_name"] == "phone-agent"
    assert inner["status"] == "ready"
    assert inner["loaded"] is True
    assert inner["error"] is None


def test_client_mods_off_invalid_json_treated_as_false():
    c = _client()
    r = c.post(
        "/api/state/client-mods-off",
        content=b"not-json",
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 200
    assert r.json() == {"success": True, "client_mods_off": False}


def test_traditional_mode_list_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    r = _client().get("/api/traditional-mode/list")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["items"] == []
