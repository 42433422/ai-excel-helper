"""Unit tests for ``app.db`` engine URL routing and caching (no real DB)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.engine import Engine

import app.db as db_mod


@pytest.fixture(autouse=True)
def _reset_engine_cache():
    with db_mod._engine_cache_lock:
        db_mod._engine_cache.clear()
        db_mod._session_local_cache.clear()
    yield
    with db_mod._engine_cache_lock:
        db_mod._engine_cache.clear()
        db_mod._session_local_cache.clear()


def test_normalize_mod_for_env_strips_special_chars():
    assert db_mod._normalize_mod_for_env("  my-mod! ") == "MY_MOD"


def test_mod_db_url_from_env_json():
    payload = json.dumps({"MOD_A": "postgresql://u:p@localhost/mod_a"})
    with patch.dict("os.environ", {"XCAGI_MOD_DATABASE_URLS": payload}, clear=False):
        assert db_mod._mod_db_url_from_env("MOD_A") == "postgresql://u:p@localhost/mod_a"
        assert db_mod._mod_db_url_from_env("MISSING") == ""


def test_mod_db_url_from_env_per_mod_key():
    with patch.dict(
        "os.environ",
        {"XCAGI_MOD_DATABASE_URL_MOD_B": "sqlite:///tmp/mod_b.db"},
        clear=False,
    ):
        assert db_mod._mod_db_url_from_env("mod-b") == "sqlite:///tmp/mod_b.db"


def test_mod_db_url_invalid_json_is_ignored():
    with patch.dict("os.environ", {"XCAGI_MOD_DATABASE_URLS": "not-json"}, clear=False):
        assert db_mod._mod_db_url_from_env("X") == ""


def test_sqlite_url_with_mod_suffix_appends_token():
    base = "sqlite:////data/xcagi.db"
    out = db_mod._sqlite_url_with_mod_suffix(base, "erp-bridge")
    assert out != base
    assert "xcagi" in out.lower()


def test_sqlite_url_memory_unchanged():
    base = "sqlite:///:memory:"
    assert db_mod._sqlite_url_with_mod_suffix(base, "mod") == base


def test_postgres_url_with_mod_db_suffix():
    base = "postgresql+psycopg://u:p@localhost:5432/xcagi"
    out = db_mod._postgres_url_with_mod_db(base, "ERP")
    assert out.endswith("__ERP") or "__erp" in out.lower()


def test_database_url_for_active_mod_uses_env_override():
    with patch.object(db_mod, "get_request_active_mod_id", return_value="M1"):
        with patch.object(db_mod, "_mod_db_url_from_env", return_value="sqlite:///override.db"):
            assert db_mod._database_url_for_active_mod("postgresql://localhost/x") == (
                "sqlite:///override.db"
            )


def test_database_url_for_active_mod_host_base_exception_fallback():
    with patch.object(db_mod, "get_request_active_mod_id", return_value="M1"):
        with patch(
            "app.db.host_base_db_api.should_use_base_database_for_path",
            side_effect=RuntimeError("ctx"),
        ):
            with patch(
                "app.http.request_context.get_current_http_request", side_effect=RuntimeError("ctx")
            ):
                base = "postgresql://localhost/xcagi"
                assert db_mod._database_url_for_active_mod(base) != ""


def test_postgres_url_with_mod_db_already_suffixed():
    base = "postgresql+psycopg://u:p@localhost:5432/xcagi__erp"
    assert db_mod._postgres_url_with_mod_db(base, "ERP") == base


def test_database_url_for_active_mod_skips_when_base_path():
    req = MagicMock()
    req.url.path = "/api/host-base/something"
    with patch.object(db_mod, "get_request_active_mod_id", return_value="M1"):
        with patch(
            "app.db.host_base_db_api.should_use_base_database_for_path",
            return_value=True,
        ):
            with patch("app.http.request_context.get_current_http_request", return_value=req):
                base = "postgresql://localhost/xcagi"
                assert db_mod._database_url_for_active_mod(base) == base


def test_get_database_url_uses_test_manager():
    mgr = MagicMock()
    mgr.is_enabled.return_value = True
    mgr.resolved_test_db_path.return_value = "/tmp/test.db"
    with patch.object(db_mod, "_get_test_db_manager", return_value=mgr):
        assert db_mod._get_database_url().startswith("sqlite:///")


def test_get_database_url_uses_database_url_env():
    with patch.object(db_mod, "_get_test_db_manager", return_value=None):
        with patch.dict("os.environ", {"DATABASE_URL": "sqlite:///env.db"}, clear=False):
            with patch.object(db_mod, "_database_url_for_active_mod", side_effect=lambda u: u):
                assert db_mod._get_database_url() == "sqlite:///env.db"


def test_create_engine_sqlite_desktop_uses_static_pool():
    with patch.dict("os.environ", {"XCAGI_DESKTOP_MODE": "true"}, clear=False):
        engine = db_mod._create_engine_for_url("sqlite:///desk.db")
        try:
            assert "StaticPool" in type(engine.pool).__name__
        finally:
            engine.dispose()


def test_create_engine_sqlite_server_uses_null_pool():
    with patch.dict("os.environ", {}, clear=False):
        engine = db_mod._create_engine_for_url("sqlite:///srv.db")
        try:
            assert "NullPool" in type(engine.pool).__name__
        finally:
            engine.dispose()


def test_engine_cache_reuses_same_url():
    url = "sqlite:///cache_test.db"
    e1 = db_mod._get_engine_for_url(url)
    e2 = db_mod._get_engine_for_url(url)
    assert e1 is e2
    db_mod.dispose_and_recreate_engine()


def test_session_local_factory_cached():
    with patch.object(db_mod, "_get_database_url", return_value="sqlite:///sess.db"):
        f1 = db_mod._get_session_local()
        f2 = db_mod._get_session_local()
        assert f1 is f2


def test_get_db_yields_and_closes_session():
    from contextlib import contextmanager

    mock_session = MagicMock()

    @contextmanager
    def fake_transaction(url, mod_id=None):
        try:
            yield mock_session
            mock_session.commit()
        except Exception:
            mock_session.rollback()
            raise
        finally:
            mock_session.close()

    with patch("app.db.db_consistency.get_consistency_manager") as mgr:
        mgr.return_value.transaction.side_effect = fake_transaction
        gen = db_mod.get_db()
        db = next(gen)
        assert db is mock_session
        gen.close()
    mock_session.close.assert_called_once()


def test_set_sqlite_pragma_executes_on_sqlite_connection():
    conn = MagicMock()
    conn.__class__.__module__ = "sqlite3"
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    db_mod.set_sqlite_pragma(conn, None)
    assert cursor.execute.called
    cursor.close.assert_called_once()


def test_engine_proxy_getattr_delegates():
    fake = MagicMock(spec=Engine)
    fake.connect = MagicMock()
    with patch.object(db_mod, "_get_engine", return_value=fake):
        assert db_mod.engine.connect is fake.connect


def test_engine_proxy_delegates_dialect():
    fake = MagicMock(spec=Engine)
    fake.dialect = MagicMock()
    fake.dialect.name = "sqlite"
    with patch.object(db_mod, "_get_engine", return_value=fake):
        assert db_mod.engine.dialect.name == "sqlite"


def test_postgres_isolated_mod_rewrites_database_name():
    base = "postgresql+psycopg://u:p@localhost:5432/xcagi"
    with patch.dict("os.environ", {"XCAGI_MOD_ISOLATED_DATABASES": "true"}, clear=False):
        out = db_mod._postgres_url_with_mod_db(base, "erp")
    assert "__" in out


def test_mod_isolated_databases_enabled():
    with patch.dict("os.environ", {"XCAGI_MOD_ISOLATED_DATABASES": "yes"}, clear=False):
        assert db_mod._mod_isolated_databases_enabled() is True


def test_database_url_for_active_extension_alias():
    with patch.object(
        db_mod, "_database_url_for_active_mod", return_value="sqlite:///x"
    ) as mock_fn:
        assert db_mod.database_url_for_active_extension("base") == "sqlite:///x"
        mock_fn.assert_called_once_with("base")


def test_sqlite_url_invalid_base_returns_unchanged():
    assert db_mod._sqlite_url_with_mod_suffix("not-a-url", "mod") == "not-a-url"


def test_database_url_for_active_mod_sqlite_suffix():
    with patch.object(db_mod, "get_request_active_mod_id", return_value="M"):
        with patch.object(db_mod, "_mod_db_url_from_env", return_value=""):
            with patch.object(
                db_mod,
                "_sqlite_url_with_mod_suffix",
                return_value="sqlite:///mod.db",
            ) as mock_sqlite:
                out = db_mod._database_url_for_active_mod("sqlite:///base.db")
    assert out == "sqlite:///mod.db"
    mock_sqlite.assert_called_once()


def test_database_url_cache_key_fallback():
    assert db_mod._database_url_cache_key("broken://") == "broken://"


def test_close_old_connections_disposes():
    eng = MagicMock()
    db_mod._engine_cache["k"] = eng
    db_mod.close_old_connections()
    eng.dispose.assert_called_once()


def test_dispose_and_recreate_engine_resets_customers_engine():
    with patch("app.application.customer_app_service.reset_customers_engine") as reset:
        db_mod.dispose_and_recreate_engine()
        reset.assert_called_once()


def test_get_test_db_manager_returns_none_on_import_error():
    with patch.dict("sys.modules", {"app.db.test_db_manager": None}):
        assert db_mod._get_test_db_manager() is None


def test_dispose_and_recreate_engine_clears_cache():
    db_mod._engine_cache["k"] = MagicMock()
    db_mod._session_local_cache["k"] = MagicMock()
    db_mod.dispose_and_recreate_engine()
    assert not db_mod._engine_cache
    assert not db_mod._session_local_cache
