import logging
import os
import threading
from pathlib import Path

from sqlalchemy import create_engine, event, pool
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import NullPool

from app.db.base import Base
from app.db.sqlite_mod_paths import mod_suffix_token, sqlite_filename_with_mod_suffix
from app.request_active_mod_ctx import get_request_active_mod_id

logger = logging.getLogger(__name__)

# 与 app/config.py 保持一致：未设置 DATABASE_URL 时默认连接本机 PostgreSQL。
_DEFAULT_DATABASE_URL = "postgresql+psycopg://xcagi:xcagi@localhost:5432/xcagi"


def _normalize_mod_for_env(mod_id: str) -> str:
    return (
        "".join(ch if ch.isalnum() else "_" for ch in str(mod_id or "").strip()).strip("_").upper()
    )


def _mod_db_url_from_env(active_mod_id: str) -> str:
    if not active_mod_id:
        return ""
    raw_json = (os.environ.get("XCAGI_MOD_DATABASE_URLS") or "").strip()
    if raw_json:
        try:
            import json

            obj = json.loads(raw_json)
            if isinstance(obj, dict):
                v = str(obj.get(active_mod_id) or "").strip()
                if v:
                    return v
        except Exception:
            logger.warning("XCAGI_MOD_DATABASE_URLS is invalid JSON; ignored")
    env_key = f"XCAGI_MOD_DATABASE_URL_{_normalize_mod_for_env(active_mod_id)}"
    return str(os.environ.get(env_key) or "").strip()


def _sqlite_url_with_mod_suffix(base_url: str, active_mod_id: str) -> str:
    """支持 sqlite:///、sqlite+pysqlite:///、sqlite+aiosqlite:/// 等 SQLAlchemy 常见写法。"""
    if not active_mod_id or not (base_url or "").strip():
        return base_url
    try:
        u = make_url(base_url)
    except Exception:
        return base_url
    if u.get_dialect().name != "sqlite":
        return base_url
    ident = (u.database or "").strip()
    if not ident or ident == ":memory:":
        return base_url
    p = Path(ident)
    new_name = sqlite_filename_with_mod_suffix(p.name, active_mod_id)
    if new_name == p.name:
        return base_url
    try:
        return u.set(database=str(p.with_name(new_name))).render_as_string(hide_password=False)
    except Exception:
        logger.warning("无法为 SQLite URL 附加 Mod 后缀，已回退原 URL", exc_info=True)
        return base_url


def _mod_isolated_databases_enabled() -> bool:
    """与 backend/mod_database_url.py、scripts/bootstrap_mod_postgres_databases.py 约定一致。"""
    return (os.environ.get("XCAGI_MOD_ISOLATED_DATABASES") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _postgres_url_with_mod_db(base_url: str, active_mod_id: str) -> str:
    """PostgreSQL：库名改为 {原库名}__{mod_suffix}（须事先建库并迁移）。"""
    if not active_mod_id or not (base_url or "").strip():
        return base_url
    suffix = mod_suffix_token(active_mod_id)
    if not suffix:
        return base_url
    try:
        u = make_url(base_url)
    except Exception:
        return base_url
    if u.get_dialect().name != "postgresql":
        return base_url
    base_db = (u.database or "xcagi").strip()
    if base_db.endswith(f"__{suffix}"):
        return base_url
    try:
        # 注意：str(URL) 会把密码打成 ***，必须用 render_as_string(hide_password=False)
        return u.set(database=f"{base_db}__{suffix}").render_as_string(hide_password=False)
    except Exception:
        logger.warning("无法为 PostgreSQL URL 附加 Mod 库名后缀，已回退原 URL", exc_info=True)
        return base_url


def _database_url_for_active_mod(base_url: str) -> str:
    active_mod_id = get_request_active_mod_id()
    if active_mod_id:
        try:
            from app.db.host_base_db_api import should_use_base_database_for_path
            from app.http.request_context import get_current_http_request

            req = get_current_http_request()
            if req is not None and should_use_base_database_for_path(
                getattr(getattr(req, "url", None), "path", "") or ""
            ):
                active_mod_id = ""
        except Exception:
            pass
    if not active_mod_id:
        return base_url
    mapped = _mod_db_url_from_env(active_mod_id)
    if mapped:
        return mapped
    try:
        u = make_url(base_url)
    except Exception:
        u = None
    if u is not None and u.get_dialect().name == "sqlite":
        return _sqlite_url_with_mod_suffix(base_url, active_mod_id)
    if u is not None and u.get_dialect().name == "postgresql" and _mod_isolated_databases_enabled():
        return _postgres_url_with_mod_db(base_url, active_mod_id)
    return base_url


def database_url_for_active_extension(base_url: str) -> str:
    """对任意基址连接串应用当前请求的扩展 Mod 选库规则（供客户库等复用）。"""
    return _database_url_for_active_mod(base_url)


def _get_test_db_manager():
    try:
        from app.db.test_db_manager import get_test_db_manager

        return get_test_db_manager()
    except Exception:
        return None


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-64000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def _get_database_url(db_path: str | None = None) -> str:
    test_mgr = _get_test_db_manager()
    if test_mgr and test_mgr.is_enabled():
        return f"sqlite:///{test_mgr.resolved_test_db_path()}"
    env_url = (os.environ.get("DATABASE_URL") or "").strip()
    if env_url:
        return _database_url_for_active_mod(env_url)
    if (os.environ.get("XCAGI_DESKTOP_MODE") or "").strip().lower() in {"1", "true", "yes", "on"}:
        from app.desktop_runtime.db import configure_sqlite_defaults

        return _database_url_for_active_mod(configure_sqlite_defaults())
    # 无 DATABASE_URL 时与 Config 一致：默认本机 PostgreSQL（请在 .env 中设置 DATABASE_URL 或使用 SQLite URL）。
    return _database_url_for_active_mod(_DEFAULT_DATABASE_URL)


def _sqlite_desktop_mode() -> bool:
    return (os.environ.get("XCAGI_DESKTOP_MODE") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _create_engine_for_url(url: str):
    if url.startswith("sqlite"):
        # 桌面单用户：StaticPool 复用单连接，降低 NullPool 每次请求的开销。
        # 服务端/多写场景仍用 NullPool，减轻 database is locked。
        if _sqlite_desktop_mode():
            return create_engine(
                url,
                connect_args={"check_same_thread": False, "timeout": 45},
                poolclass=pool.StaticPool,
                echo=False,
            )
        return create_engine(
            url,
            connect_args={"check_same_thread": False, "timeout": 45},
            poolclass=NullPool,
            echo=False,
        )
    # PostgreSQL 连接超时默认较长；显式设置可避免启动阶段“看起来卡死”。
    connect_args = {"connect_timeout": int(os.environ.get("PGCONNECT_TIMEOUT", "5"))}
    return create_engine(
        url,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
        pool_timeout=30,
        echo=False,
    )


def get_engine(db_path: str = None):
    return _create_engine_for_url(_get_database_url(db_path))


_engine_cache_lock = threading.RLock()
_engine_cache: dict[str, Engine] = {}
_session_local_cache: dict[str, sessionmaker] = {}


def _database_url_cache_key(url: str) -> str:
    try:
        return make_url(url).render_as_string(hide_password=False)
    except Exception:
        return str(url)


def _get_engine_for_url(url: str):
    key = _database_url_cache_key(url)
    with _engine_cache_lock:
        cached = _engine_cache.get(key)
        if cached is not None:
            return cached
        created = _create_engine_for_url(url)
        _engine_cache[key] = created
        return created


def _get_engine():
    return _get_engine_for_url(_get_database_url())


def _get_session_local():
    want_url = _get_database_url()
    key = _database_url_cache_key(want_url)
    with _engine_cache_lock:
        cached = _session_local_cache.get(key)
        if cached is not None:
            return cached
        created = sessionmaker(
            autocommit=False, autoflush=False, bind=_get_engine_for_url(want_url)
        )
        _session_local_cache[key] = created
        return created


# Backward-compatible export:
# Some parts of the codebase (and older modules) import `SessionLocal` from `app.db`
# and expect it to be callable (returns a SQLAlchemy Session instance).
def SessionLocal():
    return _get_session_local()()


def dispose_and_recreate_engine():
    with _engine_cache_lock:
        for cached_engine in _engine_cache.values():
            cached_engine.dispose()
        _engine_cache.clear()
        _session_local_cache.clear()
    try:
        from app.application.customer_app_service import reset_customers_engine

        reset_customers_engine()
    except Exception:
        pass


class _EngineProxy:
    @property
    def dialect(self):
        return _get_engine().dialect

    def __getattr__(self, name):
        return getattr(_get_engine(), name)


engine = _EngineProxy()


def get_db():
    SessionLocal = _get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def close_old_connections():
    with _engine_cache_lock:
        for cached_engine in _engine_cache.values():
            cached_engine.dispose()
        _engine_cache.clear()
        _session_local_cache.clear()
    logger.info("数据库连接池已刷新")
