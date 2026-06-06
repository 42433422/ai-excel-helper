from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.fastapi_routes import legacy_auth


class FakeAuthService:
    def __init__(self) -> None:
        self.login_calls: list[tuple[str, str]] = []

    def login(self, username: str, password: str) -> dict[str, Any]:
        self.login_calls.append((username, password))
        return {
            "success": True,
            "user": {
                "id": 7,
                "username": username,
                "display_name": username,
                "email": f"{username}@example.test",
                "role": "user",
            },
            "session_id": f"sid-{username}",
            "expires_at": "2099-01-01T00:00:00",
        }


@pytest.fixture()
def auth_matrix_client(monkeypatch: pytest.MonkeyPatch):
    app = FastAPI()
    app.include_router(legacy_auth.router)

    fake_auth = FakeAuthService()
    saved_tokens: list[tuple[str, str, str | None]] = []
    persisted_meta: list[dict[str, Any]] = []
    market_login: Callable[[str, str], Any] | None = None

    def set_market_login(func: Callable[[str, str], Any]) -> None:
        nonlocal market_login
        market_login = func

    async def fake_market_login(username: str, password: str) -> dict[str, Any]:
        assert market_login is not None
        return market_login(username, password)

    def fake_save_session_market_token(
        session_id: str,
        token: str,
        refresh_token: str | None = None,
    ) -> None:
        saved_tokens.append((session_id, token, refresh_token))

    def fake_persist_session_account_meta(session_id: str, **kwargs: Any) -> None:
        persisted_meta.append({"session_id": session_id, **kwargs})

    async def fake_refresh_session_entitlements_from_market(**_kwargs: Any) -> set[str]:
        return set()

    async def fake_reload_enterprise_mods_after_login() -> None:
        return None

    monkeypatch.setattr("app.mod_sdk.product_skus.resolve_product_sku", lambda: "enterprise")
    monkeypatch.setattr("app.application.auth_app_service.get_auth_app_service", lambda: fake_auth)
    monkeypatch.setattr(
        "app.fastapi_routes.market_account.login_market_with_password", fake_market_login
    )
    monkeypatch.setattr(
        "app.fastapi_routes.market_account.save_session_market_token",
        fake_save_session_market_token,
    )
    monkeypatch.setattr(
        "app.application.session_account_meta.persist_session_account_meta",
        fake_persist_session_account_meta,
    )
    monkeypatch.setattr(
        "app.enterprise.mod_entitlements.refresh_session_entitlements_from_market",
        fake_refresh_session_entitlements_from_market,
    )
    monkeypatch.setattr(
        "app.enterprise.mod_entitlements.persist_entitlements_to_session_row", lambda *args: None
    )
    monkeypatch.setattr(
        "app.enterprise.mod_entitlements.reload_enterprise_mods_after_login",
        fake_reload_enterprise_mods_after_login,
    )
    monkeypatch.setattr(
        "app.enterprise.mod_entitlements.get_cached_entitled_client_mod_ids", lambda: set()
    )
    monkeypatch.setattr(
        "app.enterprise.account_mod_binding.augment_entitled_client_mod_ids_for_username",
        lambda *args: set(),
    )

    return {
        "client": TestClient(app, raise_server_exceptions=False),
        "auth": fake_auth,
        "set_market_login": set_market_login,
        "saved_tokens": saved_tokens,
        "persisted_meta": persisted_meta,
    }


def market_identity_result(
    *,
    username: str = "demo",
    is_enterprise: bool,
    is_market_admin: bool,
) -> dict[str, Any]:
    return {
        "success": True,
        "market_base_url": "http://market.example.test",
        "token": f"token-{username}",
        "refresh_token": f"refresh-{username}",
        "is_enterprise": is_enterprise,
        "is_market_admin": is_market_admin,
        "raw": {
            "user": {
                "id": 42,
                "username": username,
                "company": "修茈测试企业",
                "is_enterprise": is_enterprise,
                "is_admin": is_market_admin,
            }
        },
    }


def post_login(ctx: dict[str, Any], account_kind: str):
    return ctx["client"].post(
        "/api/auth/login",
        json={"username": "demo", "password": "secret123", "account_kind": account_kind},
    )


def test_管理员账号走管理员入口成功(auth_matrix_client):
    ctx = auth_matrix_client
    ctx["set_market_login"](
        lambda username, _password: market_identity_result(
            username=username,
            is_enterprise=False,
            is_market_admin=True,
        )
    )

    response = post_login(ctx, "admin")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["account_kind"] == "admin"
    assert body["market_is_admin"] is True
    assert ctx["auth"].login_calls == [("demo", "secret123")]
    assert ctx["saved_tokens"] == [("sid-demo", "token-demo", "refresh-demo")]
    assert ctx["persisted_meta"][0]["account_kind"] == "admin"


def test_管理员账号走企业入口返回_403(auth_matrix_client):
    ctx = auth_matrix_client
    ctx["set_market_login"](
        lambda username, _password: market_identity_result(
            username=username,
            is_enterprise=True,
            is_market_admin=True,
        )
    )

    response = post_login(ctx, "enterprise")

    assert response.status_code == 403
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "ACCOUNT_KIND_MISMATCH"
    assert "管理员入口" in body["error"]["message"]
    assert ctx["auth"].login_calls == []
    assert ctx["saved_tokens"] == []
    assert ctx["persisted_meta"] == []


def test_企业账号走企业入口成功(auth_matrix_client):
    ctx = auth_matrix_client
    ctx["set_market_login"](
        lambda username, _password: market_identity_result(
            username=username,
            is_enterprise=True,
            is_market_admin=False,
        )
    )

    response = post_login(ctx, "enterprise")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["account_kind"] == "enterprise"
    assert body["market_is_enterprise"] is True
    assert body["market_is_admin"] is False
    assert ctx["auth"].login_calls == [("demo", "secret123")]
    assert ctx["persisted_meta"][0]["company_brand"] == "修茈测试企业"


@pytest.mark.parametrize(
    ("is_enterprise", "is_market_admin"),
    [(True, False), (False, False)],
)
def test_非管理员账号走管理员入口返回_403(
    auth_matrix_client,
    is_enterprise: bool,
    is_market_admin: bool,
):
    ctx = auth_matrix_client
    ctx["set_market_login"](
        lambda username, _password: market_identity_result(
            username=username,
            is_enterprise=is_enterprise,
            is_market_admin=is_market_admin,
        )
    )

    response = post_login(ctx, "admin")

    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "ACCOUNT_KIND_MISMATCH"
    assert "平台管理员账号" in body["error"]["message"]
    assert ctx["auth"].login_calls == []
    assert ctx["saved_tokens"] == []


def test_市场不可达时管理员入口不创建本地会话(auth_matrix_client):
    ctx = auth_matrix_client
    ctx["set_market_login"](
        lambda _username, _password: {
            "success": False,
            "message": "市场服务返回 502（服务器内部错误）。请检查 XCAGI_MARKET_BASE_URL=http://127.0.0.1:8765",
            "status_code": 502,
            "market_base_url": "http://127.0.0.1:8765",
        }
    )

    response = post_login(ctx, "admin")

    assert response.status_code == 502
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "MARKET_AUTH_UNAVAILABLE"
    assert "市场服务返回 502" in body["error"]["message"]
    assert ctx["auth"].login_calls == []
    assert ctx["saved_tokens"] == []
    assert ctx["persisted_meta"] == []
