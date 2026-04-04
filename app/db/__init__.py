import logging
import os

from sqlalchemy import create_engine, event, pool
from sqlalchemy.engine import Engine
from sqlalchemy.orm import scoped_session, sessionmaker

from app.db.base import Base
from app.db.init_db import get_db_path

logger = logging.getLogger(__name__)


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
        return f"sqlite:///{test_mgr._test_db_path}"
    env_url = (os.environ.get("DATABASE_URL") or "").strip()
    if env_url:
        return env_url
    path = db_path or get_db_path("products.db")
    return f"sqlite:///{path}"


def get_engine(db_path: str = None):
    url = _get_database_url(db_path)
    if url.startswith("sqlite"):
        return create_engine(
            url,
            connect_args={"check_same_thread": False, "timeout": 30},
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,
            pool_timeout=30,
            echo=False,
        )
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
        pool_timeout=30,
        echo=False,
    )


_engine = None
_SessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = get_engine()
    else:
        url = _get_database_url()
        expected_db = (_get_test_db_manager()._test_db_path if _get_test_db_manager() and _get_test_db_manager().is_enabled() else get_db_path("products.db"))
        current_db = getattr(_engine.url, 'database', None)
        if current_db != expected_db:
            _engine.dispose()
            _engine = get_engine()
    return _engine


def _get_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_get_engine())
    return _SessionLocal


# Backward-compatible export:
# Some parts of the codebase (and older modules) import `SessionLocal` from `app.db`
# and expect it to be callable (returns a SQLAlchemy Session instance).
def SessionLocal():
    return _get_session_local()()


def dispose_and_recreate_engine():
    global _engine, _SessionLocal
    if _engine:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


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
    global _engine, _SessionLocal
    if _engine:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
    logger.info("数据库连接池已刷新")
