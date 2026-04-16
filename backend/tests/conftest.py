"""
Pytest 配置：优先使用已有 DATABASE_URL / FHD_TEST_DATABASE_URL；
若本机固定地址连不上且 Docker 可用，则自动用 Testcontainers 启动临时 PostgreSQL。
"""

from __future__ import annotations

import atexit
import os
import subprocess

import pandas as pd
import pytest


def _is_postgres_url(u: str) -> bool:
    x = (u or "").strip().lower()
    return x.startswith("postgresql") or x.startswith("postgres")


_FALLBACK_LOCAL = "postgresql+psycopg://xcagi:xcagi@127.0.0.1:5432/xcagi_test"

_existing = os.environ.get("DATABASE_URL", "").strip()
if _is_postgres_url(_existing):
    pass
else:
    _alt = os.environ.get("FHD_TEST_DATABASE_URL", "").strip()
    if _is_postgres_url(_alt):
        os.environ["DATABASE_URL"] = _alt
    else:
        os.environ["DATABASE_URL"] = _FALLBACK_LOCAL

_url = os.environ.get("DATABASE_URL", "").strip()
if not _is_postgres_url(_url):
    from _pytest.outcomes import Skipped

    raise Skipped(
        "DATABASE_URL must be a PostgreSQL URL (postgresql:// or postgres://).",
        allow_module_level=True,
    ) from None

# pytest 不依赖 XCAGI/mods；避免与生产一致的「无扩展 Mod 则业务读为空」导致产品等 API 全空
os.environ["FHD_BUSINESS_DATA_REQUIRES_EXTENSION_MOD"] = "0"

_TC_PG_CONTAINER = None


def _pg_ping(url: str, *, timeout: int = 8) -> bool:
    try:
        from sqlalchemy import create_engine, text

        eng = create_engine(
            url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": timeout},
        )
        try:
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
        finally:
            eng.dispose()
        return True
    except Exception:
        return False


def _docker_daemon_up() -> bool:
    try:
        r = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=25,
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def _start_testcontainers_postgres() -> str | None:
    """
    返回可用的 postgresql+psycopg:// URL；失败返回 None。
    仅在 Docker 守护进程可用时尝试。
    """
    global _TC_PG_CONTAINER

    if not _docker_daemon_up():
        return None
    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError:
        return None

    c = None
    try:
        c = PostgresContainer("postgres:16-alpine", driver="psycopg")
        c.start()
        url = c.get_connection_url()
        if not _is_postgres_url(url):
            return None
        _TC_PG_CONTAINER = c

        def _stop_tc() -> None:
            global _TC_PG_CONTAINER
            if _TC_PG_CONTAINER is not None:
                try:
                    _TC_PG_CONTAINER.stop()
                except Exception:
                    pass
                _TC_PG_CONTAINER = None

        atexit.register(_stop_tc)
        return url
    except Exception:
        if c is not None:
            try:
                c.stop()
            except Exception:
                pass
        return None


if not _pg_ping(os.environ["DATABASE_URL"]):
    _spun = _start_testcontainers_postgres()
    if _spun:
        os.environ["DATABASE_URL"] = _spun
        try:
            from backend.database import dispose_sync_engine

            dispose_sync_engine()
        except Exception:
            pass
        if not _pg_ping(_spun):
            from _pytest.outcomes import Skipped

            raise Skipped(
                "Testcontainers PostgreSQL started but not reachable; try increasing wait or "
                "check Docker networking.",
                allow_module_level=True,
            ) from None
    else:
        from _pytest.outcomes import Skipped

        raise Skipped(
            "PostgreSQL unreachable and Docker not available to auto-start a test database. "
            "Options: (1) Start Docker Desktop then re-run pytest (Testcontainers will start Postgres). "
            "(2) Run scripts/docker-postgres-for-fhd.bat. "
            "(3) Set DATABASE_URL or FHD_TEST_DATABASE_URL to a reachable postgresql+psycopg://... URL.",
            allow_module_level=True,
        ) from None


@pytest.fixture(scope="session", autouse=True)
def _fhd_pg_session_cleanup():
    yield
    try:
        from backend.database import dispose_sync_engine

        dispose_sync_engine()
    except Exception:
        pass


@pytest.fixture
def excel_workspace(tmp_path):
    df = pd.DataFrame(
        {
            "Name": ["Alice", "Bob", "Carol"],
            "Age": [30, 25, 40],
            "Dept": ["Eng", "Sales", "Eng"],
        }
    )
    path = tmp_path / "sample.xlsx"
    df.to_excel(path, index=False)
    return tmp_path
