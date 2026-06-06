"""移动端 API 扩展路由测试。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("LAN_GUARD_ENABLED", "0")
    monkeypatch.setenv("LAN_CIDR_GUARD_ENABLED", "0")
    from app.fastapi_app.factory import create_fastapi_app

    return TestClient(create_fastapi_app(enable_cors=False))


def test_pairing_issue_and_exchange(client: TestClient):
    issue = client.post(
        "/api/mobile/v1/pairing/issue",
        json={"host": "192.168.1.10", "port": 5000},
    )
    assert issue.status_code == 200
    body = issue.json()
    assert body.get("success") is True
    nonce = body.get("data", {}).get("nonce")
    assert nonce
    ex = client.post("/api/mobile/v1/pairing/exchange", json={"nonce": nonce})
    assert ex.status_code == 200
    assert ex.json().get("data", {}).get("host") == "192.168.1.10"


def test_mobile_mods_requires_auth(client: TestClient):
    r = client.get("/api/mobile/v1/mods")
    assert r.status_code in (401, 403)
