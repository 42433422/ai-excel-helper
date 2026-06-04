"""Sync engine / database mode / mod-aware URL resolution.

import logging

logger = logging.getLogger(__name__)
Phase 5B 从 ``app.legacy.database`` + ``app.legacy.mod_database_url`` 吸收。
对外接口与 legacy 完全一致,曾经 ``from app.legacy.database import ...``
的调用方改为 ``from app.infrastructure.db.sync_engine import ...``。
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.infrastructure.db.mod_database_url import resolve_database_url_for_active_mod
from app.shell import mod_database_gate

# get_sync_engine() 持锁期间会调用 resolve_mode()/get_database_url()，
# 需支持同线程重入避免自锁死。
_lock = threading.RLock()
_mode: Literal["production", "test"] = "production"
_engine: Engine | None = None
_bound_engine_url: str | None = None


def _workspace_root() -> Path:
    return Path(os.environ.get("WORKSPACE_ROOT", os.getcwd())).resolve()


def resolve_mode() -> Literal["production", "test"]:
    with _lock:
        return _mode


def set_mode(mode: str) -> None:
    if mode not in ("production", "test"):
        raise ValueError("mode must be production or test")
    global _mode, _engine, _bound_engine_url
    with _lock:
        _mode = mode  # type: ignore[assignment]
        _engine = None
        _bound_engine_url = None


def _sqlite_path_for_mode(mode: Literal["production", "test"]) -> Path:
    name = "products.db" if mode == "production" else "products_test.db"
    return _workspace_root() / name


def resolve_customer_db_path() -> Path:
    return _sqlite_path_for_mode(resolve_mode())


def _database_url_for_mode(mode: Literal["production", "test"]) -> str:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        db_path = _sqlite_path_for_mode(mode)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path.as_posix()}"
    env_url = (os.environ.get("DATABASE_URL") or "").strip()
    if env_url:
        return env_url
    db_path = _sqlite_path_for_mode(mode)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path.as_posix()}"


def get_database_url() -> str:
    gate = mod_database_gate.mod_db_gate_state()
    if not gate.get("gate_open", True):
        raise RuntimeError(f"database_mod_gate_closed: {gate.get('reason') or 'blocked'}")
    base = _database_url_for_mode(resolve_mode())
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return base
    return resolve_database_url_for_active_mod(base)


def _urls_equivalent(a: str | None, b: str) -> bool:
    if a is None:
        return False
    try:
        from sqlalchemy.engine import make_url

        return make_url(a).render_as_string(hide_password=True) == make_url(b).render_as_string(
            hide_password=True
        )
    except Exception:
        return (a or "").strip() == (b or "").strip()


def get_sync_engine() -> Engine:
    global _engine, _bound_engine_url
    with _lock:
        if os.environ.get("PYTEST_CURRENT_TEST"):
            if _engine is None:
                db_path = _workspace_root() / ".pytest_products.db"
                _engine = create_engine(
                    f"sqlite:///{db_path.as_posix()}",
                    future=True,
                    connect_args={"timeout": 1},
                )
                _bound_engine_url = str(_engine.url)
            return _engine
        want = get_database_url()
        if _engine is None or not _urls_equivalent(_bound_engine_url, want):
            if _engine is not None:
                _engine.dispose()
            _engine = create_engine(want, future=True)
            _bound_engine_url = want
        return _engine


def dispose_sync_engine() -> None:
    global _engine, _bound_engine_url
    with _lock:
        if _engine is not None:
            _engine.dispose()
        _engine = None
        _bound_engine_url = None


def redact_database_url(url: str) -> str:
    try:
        p = urlparse(url)
        if p.password:
            user = p.username or ""
            host = p.hostname or ""
            port = f":{p.port}" if p.port else ""
            return f"{p.scheme}://{user}:***@{host}{port}{p.path or ''}"
    except Exception:
        logger.debug("suppressed exception", exc_info=True)
    return url


def get_db_status() -> dict[str, Any]:
    mode = resolve_mode()
    gate = mod_database_gate.mod_db_gate_state()
    if not gate.get("gate_open", True):
        return {
            "mode": mode,
            "backend": "postgresql",
            "database_mod_gate_closed": True,
            "mod_database_gate": gate,
            "database_url": None,
            "current_db": None,
            "current_db_name": "postgresql",
            "production_db": {"path": None, "exists": False},
            "test_db": {"path": None, "exists": False},
            "postgresql_summary": {"database_name": "", "host_port": "", "redacted_url": ""},
        }
    url = get_database_url()
    parsed = urlparse(url)
    current_name = (
        parsed.path.rsplit("/", 1)[-1]
        if parsed.path
        else ("postgresql" if "postgres" in parsed.scheme else "database")
    )
    return {
        "mode": mode,
        "backend": "postgresql" if "postgres" in parsed.scheme else "sqlite",
        "database_url": redact_database_url(url),
        "current_db": redact_database_url(url),
        "current_db_name": current_name,
        "production_db": {
            "path": str(_sqlite_path_for_mode("production")),
            "exists": _sqlite_path_for_mode("production").exists(),
        },
        "test_db": {
            "path": str(_sqlite_path_for_mode("test")),
            "exists": _sqlite_path_for_mode("test").exists(),
        },
        "postgresql_summary": {
            "database_name": current_name if "postgres" in parsed.scheme else "",
            "host_port": (
                f"{parsed.hostname or ''}{':' + str(parsed.port) if parsed.port else ''}"
                if parsed.hostname
                else ""
            ),
            "redacted_url": redact_database_url(url),
        },
        "mod_database_gate": gate,
    }


def postgresql_connection_summary(url: str) -> dict[str, str]:
    p = urlparse(url.replace("postgresql+psycopg", "postgresql", 1))
    dbn = (p.path or "").lstrip("/")
    hp = f"{p.hostname or ''}{':' + str(p.port) if p.port else ''}".strip(":")
    return {
        "database_name": dbn,
        "host_port": hp,
        "redacted_url": redact_database_url(url),
    }


def switch_to_production_mode() -> dict[str, Any]:
    set_mode("production")
    return {"success": True, "mode": "production"}


def switch_to_test_mode() -> dict[str, Any]:
    set_mode("test")
    return {"success": True, "mode": "test"}


def reset_test_db() -> dict[str, Any]:
    p = _sqlite_path_for_mode("test")
    try:
        if p.exists():
            p.unlink()
    except OSError:
        return {"success": False, "error": True, "message": f"failed to remove {p}"}
    return {"success": True, "mode": "test", "path": str(p)}


__all__ = [
    "resolve_mode",
    "set_mode",
    "resolve_customer_db_path",
    "get_database_url",
    "get_sync_engine",
    "dispose_sync_engine",
    "redact_database_url",
    "get_db_status",
    "postgresql_connection_summary",
    "switch_to_production_mode",
    "switch_to_test_mode",
    "reset_test_db",
    "resolve_database_url_for_active_mod",
]
