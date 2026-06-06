"""移动端 API 路由测试。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("LAN_GUARD_ENABLED", "0")
    monkeypatch.setenv("LAN_CIDR_GUARD_ENABLED", "0")
    from app.fastapi_app.factory import create_fastapi_app

    app = create_fastapi_app(enable_cors=False)
    return TestClient(app)


def test_mobile_health(client: TestClient):
    r = client.get("/api/mobile/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True
    assert body.get("data", {}).get("status") == "ok"


def test_mobile_discover_hint(client: TestClient):
    r = client.get("/api/mobile/v1/host/discover-hint")
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True
    assert "lan" in body.get("data", {})


def test_mobile_login_invalid(client: TestClient):
    r = client.post(
        "/api/mobile/v1/auth/login",
        json={"username": "nonexistent_user_xyz", "password": "wrong"},
    )
    assert r.status_code in (401, 403)
