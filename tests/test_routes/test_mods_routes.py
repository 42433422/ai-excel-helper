from __future__ import annotations

from fastapi import FastAPI
from starlette.testclient import TestClient

from app.fastapi_routes.mods_routes import get_mods_router


class _FakeModManager:
    def list_all_mods(self):
        return [{"id": "demo-mod", "name": "Demo Mod"}]

    def _mods_scan_fingerprint(self):
        return "test-fingerprint"


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(get_mods_router())
    return TestClient(app)


def test_list_mods_accepts_no_trailing_slash(monkeypatch):
    monkeypatch.setattr(
        "app.infrastructure.mods.mod_manager.get_mod_manager",
        lambda: _FakeModManager(),
    )

    with _client() as client:
        response = client.get("/api/mods")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": [{"id": "demo-mod", "name": "Demo Mod"}],
    }


def test_list_mods_keeps_trailing_slash_route(monkeypatch):
    monkeypatch.setattr(
        "app.infrastructure.mods.mod_manager.get_mod_manager",
        lambda: _FakeModManager(),
    )

    with _client() as client:
        response = client.get("/api/mods/")

    assert response.status_code == 200
    assert response.json()["success"] is True
