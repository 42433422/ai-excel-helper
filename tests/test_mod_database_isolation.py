import asyncio
from pathlib import Path

from sqlalchemy.engine import make_url


def test_postgres_active_mod_database_url_suffix(monkeypatch):
    from app import db
    from app.request_active_mod_ctx import reset_request_active_mod_id, set_request_active_mod_id

    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:secret@localhost:5432/xcagi")
    monkeypatch.setenv("XCAGI_MOD_ISOLATED_DATABASES", "1")

    token = set_request_active_mod_id("leshan-kc-ai-suite-test")
    try:
        url = db._get_database_url()
    finally:
        reset_request_active_mod_id(token)

    parsed = make_url(url)
    assert parsed.database == "xcagi__leshan_kc_ai_suite_test"
    assert "secret" in parsed.render_as_string(hide_password=False)


def test_session_factories_are_cached_per_resolved_database_url(monkeypatch, tmp_path):
    from app import db
    from app.request_active_mod_ctx import reset_request_active_mod_id, set_request_active_mod_id

    db.dispose_and_recreate_engine()
    base_path = tmp_path / "xcagi.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{base_path}")
    monkeypatch.delenv("XCAGI_MOD_DATABASE_URLS", raising=False)

    base_factory = db._get_session_local()

    token = set_request_active_mod_id("taiyangniao-pro")
    try:
        mod_factory = db._get_session_local()
        mod_url = db._get_database_url()
    finally:
        reset_request_active_mod_id(token)

    base_factory_again = db._get_session_local()

    assert base_factory_again is base_factory
    assert mod_factory is not base_factory
    assert Path(make_url(mod_url).database or "").name == "xcagi__taiyangniao_pro.db"

    db.dispose_and_recreate_engine()


def test_mod_context_middleware_infers_active_mod_from_api_path():
    from app.infrastructure.mods.mod_auth import ModContextMiddleware
    from app.request_active_mod_ctx import get_request_active_mod_id

    seen: dict[str, str] = {}

    async def downstream(scope, receive, send):
        seen["active_mod"] = get_request_active_mod_id()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(_message):
        return None

    middleware = ModContextMiddleware(downstream)
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/mod/leshan-kc-ai-suite-test/status",
        "headers": [],
        "query_string": b"",
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 12345),
    }

    asyncio.run(middleware(scope, receive, send))

    assert seen["active_mod"] == "leshan-kc-ai-suite-test"
    assert get_request_active_mod_id() == ""


def test_mod_context_header_takes_priority_over_path():
    from app.infrastructure.mods.mod_auth import ModContextMiddleware
    from app.request_active_mod_ctx import get_request_active_mod_id

    seen: dict[str, str] = {}

    async def downstream(scope, receive, send):
        seen["active_mod"] = get_request_active_mod_id()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(_message):
        return None

    middleware = ModContextMiddleware(downstream)
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/mod/path-mod/status",
        "headers": [(b"x-xcagi-active-mod-id", b"header-mod")],
        "query_string": b"",
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 12345),
    }

    asyncio.run(middleware(scope, receive, send))

    assert seen["active_mod"] == "header-mod"
    assert get_request_active_mod_id() == ""
