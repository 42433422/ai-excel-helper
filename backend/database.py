"""
数据库访问与模式说明（与 XCAGI 对齐）：

- **仅支持 PostgreSQL**：``DATABASE_URL`` 必须为 ``postgresql://`` / ``postgres://`` / ``postgresql+psycopg://`` 等；
  禁止使用 ``sqlite:`` 连接串。
- 未设置 ``DATABASE_URL`` 时使用 ``FHD_DEFAULT_DATABASE_URL`` 或本机默认
  ``postgresql+psycopg://xcagi:xcagi@localhost:5432/xcagi``。
- 业务数据一律经 SQLAlchemy ``get_sync_engine()``；不再提供本地 ``products.db`` / ``customers.db`` 文件路径解析。
"""

from __future__ import annotations

import logging
import os
import sqlite3
import shutil
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_DB_MODE_KEY = "FHD_DB_MODE"
_DEFAULT_DB_MODE: Literal["production", "test"] = "production"
_current_mode: Literal["production", "test"] | None = None

_TEST_DB_NAME = "products_test.db"
_PRODUCTION_DB_NAME = "products.db"
_CUSTOMERS_DB_NAME = "customers.db"

_DEFAULT_POSTGRES_URL = "postgresql+psycopg://xcagi:xcagi@localhost:5432/xcagi"

_sync_engine: Any = None


def _get_db_dir() -> Path:
    """获取数据库目录，优先从环境变量，其次尝试常见路径。"""
    db_dir = os.environ.get("FHD_DB_DIR", "").strip()
    if db_dir and os.path.isdir(db_dir):
        return Path(db_dir)

    fallback_dirs = [
        Path("e:/FHD/xcagi"),
        Path("e:/FHD/424"),
        Path.cwd(),
    ]
    for d in fallback_dirs:
        if d.is_dir() and (d / _PRODUCTION_DB_NAME).is_file():
            return d
    for d in fallback_dirs:
        if d.is_dir():
            return d
    return Path.cwd()


def _get_production_db_path() -> Path:
    return _get_db_dir() / _PRODUCTION_DB_NAME


def _get_test_db_path() -> Path:
    return _get_db_dir() / _TEST_DB_NAME


def _discover_sqlite_products_path() -> Path | None:
    """不读取 DATABASE_URL 时，用于推断 products.db 文件路径。"""
    env = os.environ.get("FHD_PRODUCTS_DB", "").strip()
    if env:
        p = Path(env).expanduser()
        return p.resolve() if p.is_file() else None
    mode = resolve_mode()
    path = _get_test_db_path() if mode == "test" else _get_production_db_path()
    return path.resolve() if path.is_file() else None


def _sqlite_path_from_database_url(url: str) -> Path | None:
    raw = (url or "").strip()
    if not raw.lower().startswith("sqlite"):
        return None
    u = urlparse(raw.replace("\\", "/"))
    if u.scheme != "sqlite":
        return None
    p = (u.path or "").strip()
    if not p or ":memory:" in p:
        return None
    return Path(p).expanduser().resolve()


def _reject_non_postgresql_url(url: str) -> None:
    u = (url or "").strip().lower()
    if u.startswith("sqlite"):
        raise RuntimeError(
            "FHD 后端已改为仅支持 PostgreSQL：请勿使用 sqlite 的 DATABASE_URL。"
            " 请设置 postgresql+psycopg://... 或 postgres://... 连接串。"
        )
    if not (u.startswith("postgresql") or u.startswith("postgres")):
        raise RuntimeError(
            "FHD 仅支持 PostgreSQL：DATABASE_URL 须以 postgresql:// 或 postgres:// 开头。"
        )


def get_database_url() -> str:
    """单一连接串：仅 PostgreSQL。"""
    from backend.shell.mod_database_gate import enforce_mod_database_gate_for_url

    enforce_mod_database_gate_for_url()
    explicit = os.environ.get("DATABASE_URL", "").strip()
    if explicit:
        _reject_non_postgresql_url(explicit)
        return explicit
    out = os.environ.get("FHD_DEFAULT_DATABASE_URL", _DEFAULT_POSTGRES_URL).strip() or _DEFAULT_POSTGRES_URL
    _reject_non_postgresql_url(out)
    return out


def database_url_is_postgresql(url: str | None = None) -> bool:
    u = (url or get_database_url()).strip().lower()
    return u.startswith("postgresql") or u.startswith("postgres")


def get_sync_engine():
    """SQLAlchemy 同步引擎（PostgreSQL），惰性单例。"""
    global _sync_engine
    if _sync_engine is not None:
        return _sync_engine
    try:
        from sqlalchemy import create_engine
    except ImportError as e:
        raise RuntimeError("需要安装 sqlalchemy 才能使用 DATABASE_URL 数据库访问") from e

    url = get_database_url()
    # Fail fast when PostgreSQL is unreachable; otherwise request handlers can block
    # for a long time on the first DB access and make the frontend appear frozen.
    kwargs: dict[str, Any] = {
        "pool_pre_ping": True,
        "pool_timeout": 5,
        "connect_args": {
            "connect_timeout": int(os.environ.get("FHD_DB_CONNECT_TIMEOUT", "5")),
        },
    }
    _sync_engine = create_engine(url, **kwargs)
    try:
        from backend.schema_auto_init import (
            ensure_document_templates_schema,
            ensure_mod_row_scope_columns,
            ensure_pg_core_business_tables,
        )

        ensure_pg_core_business_tables(_sync_engine)
        ensure_document_templates_schema(_sync_engine)
        ensure_mod_row_scope_columns(_sync_engine)
        try:
            from backend.document_template_legacy_migration import (
                migrate_legacy_document_template_files,
                sync_document_templates_storage_after_layout_migration,
            )

            migrate_legacy_document_template_files()
            sync_document_templates_storage_after_layout_migration(_sync_engine)
        except Exception as e:
            logger.warning("document_templates 磁盘布局迁移未执行或失败（可忽略）：%s", e)
        try:
            from backend.shell.mod_database_gate import apply_mod_database_seeds

            apply_mod_database_seeds(_sync_engine)
        except Exception as e:
            logger.warning("Mod 数据库种子 SQL 未执行或失败：%s", e)
    except Exception as e:
        logger.warning("PostgreSQL 核心表自动初始化未执行或失败（可设 FHD_AUTO_INIT_PG_SCHEMA=0 关闭）：%s", e)
    return _sync_engine


def dispose_sync_engine() -> None:
    """测试或热重载时释放连接池。"""
    global _sync_engine
    if _sync_engine is not None:
        _sync_engine.dispose()
        _sync_engine = None


def redact_database_url(url: str) -> str:
    """日志 / API 展示用脱敏。"""
    try:
        p = urlparse(url.replace("postgresql+psycopg", "postgresql", 1))
        if p.password:
            netloc = f"{p.username or ''}:***@{p.hostname or ''}"
            if p.port:
                netloc += f":{p.port}"
            return url.split("://", 1)[0] + "://" + netloc + (p.path or "")
    except Exception:
        pass
    return url


def postgresql_connection_summary(url: str) -> dict[str, str]:
    """从 DATABASE_URL 提取库名与主机（不含口令），供设置页与 Mod 控制台展示。"""
    raw = (url or "").strip()
    out: dict[str, str] = {"database_name": "", "host_port": "", "redacted_url": ""}
    if not raw:
        return out
    out["redacted_url"] = redact_database_url(raw)
    try:
        p = urlparse(raw.replace("postgresql+psycopg", "postgresql", 1))
        path = (p.path or "").strip().lstrip("/")
        if "?" in path:
            path = path.split("?", 1)[0]
        db_name = path or "postgres"
        host = p.hostname or ""
        port = p.port
        if host and port:
            host_port = f"{host}:{port}"
        elif host:
            host_port = host
        elif port:
            host_port = str(port)
        else:
            host_port = ""
        out["database_name"] = db_name
        out["host_port"] = host_port
    except Exception:
        pass
    return out


def resolve_products_db_path() -> Path | None:
    """保留函数名；仅 PostgreSQL 模式下恒为 None。"""
    return None


def resolve_customers_db_path() -> Path | None:
    """保留函数名；仅 PostgreSQL 模式下恒为 None。"""
    return None


def _create_blank_db(db_path: Path) -> bool:
    try:
        if db_path.exists():
            db_path.unlink()
        conn = sqlite3.connect(str(db_path))
        conn.close()
        logger.info("Created blank database: %s", db_path)
        return True
    except Exception as e:
        logger.error("Failed to create blank database %s: %s", db_path, e)
        return False


def resolve_mode() -> Literal["production", "test"]:
    global _current_mode
    if _current_mode is not None:
        return _current_mode
    env_val = os.environ.get(_DB_MODE_KEY, _DEFAULT_DB_MODE).strip().lower()
    if env_val == "test":
        _current_mode = "test"
    else:
        _current_mode = "production"
    return _current_mode


def set_mode(mode: Literal["production", "test"]) -> dict:
    global _current_mode

    if database_url_is_postgresql():
        target = mode.strip().lower()
        if target not in ("production", "test"):
            return {"error": "invalid_mode", "message": "mode must be 'production' or 'test'"}
        _current_mode = "test" if target == "test" else "production"
        os.environ[_DB_MODE_KEY] = _current_mode
        return {
            "mode": _current_mode,
            "backend": "postgresql",
            "message": "PostgreSQL：未切换本地 SQLite 文件；仅更新 API 兼容用的 mode 标记。",
            "database_url": redact_database_url(get_database_url()),
        }

    target_mode = mode.strip().lower()
    if target_mode not in ("production", "test"):
        return {"error": "invalid_mode", "message": "mode must be 'production' or 'test'"}

    test_db_path = _get_test_db_path()
    prod_db_path = _get_production_db_path()

    if target_mode == "test":
        if not test_db_path.exists():
            if not _create_blank_db(test_db_path):
                return {"error": "create_test_db_failed", "message": f"Failed to create {test_db_path}"}
        _current_mode = "test"
        os.environ[_DB_MODE_KEY] = "test"
        logger.info("Database mode switched to TEST: %s", test_db_path)
        return {
            "mode": "test",
            "current_db": str(test_db_path),
            "message": f"已切换到测试模式，当前数据库：{_TEST_DB_NAME}",
        }
    _current_mode = "production"
    os.environ[_DB_MODE_KEY] = "production"
    logger.info("Database mode switched to PRODUCTION: %s", prod_db_path)
    return {
        "mode": "production",
        "current_db": str(prod_db_path),
        "message": f"已切换到生产模式，当前数据库：{_PRODUCTION_DB_NAME}",
    }


def reset_test_db() -> dict:
    if database_url_is_postgresql():
        return {
            "status": "skipped",
            "message": "PostgreSQL 模式下不使用本地 products_test.db 文件重置。",
            "backend": "postgresql",
        }

    test_db_path = _get_test_db_path()
    if test_db_path.exists():
        try:
            test_db_path.unlink()
            logger.info("Deleted existing test database: %s", test_db_path)
        except Exception as e:
            return {"error": "delete_failed", "message": f"Failed to delete test DB: {e}"}

    if _create_blank_db(test_db_path):
        return {
            "status": "reset",
            "current_db": str(test_db_path),
            "message": "测试数据库已重置为空，可重复使用",
        }
    return {"error": "reset_failed", "message": "Failed to create blank test database"}


def get_db_status() -> dict:
    from backend.shell.mod_database_gate import mod_database_gate_status

    gate = mod_database_gate_status()
    try:
        url = get_database_url()
    except RuntimeError as e:
        if "database_mod_gate_closed" in str(e):
            try:
                from backend.shell.mod_database_gate import mod_database_seed_plan_dict

                seed_plan = mod_database_seed_plan_dict()
            except Exception as ex:
                logger.warning("mod_database_seed_plan 构建失败: %s", ex)
                seed_plan = {"mods": [], "error": str(ex)}
            return {
                "mode": resolve_mode(),
                "backend": "postgresql",
                "database_mod_gate_closed": True,
                "mod_database_gate": gate,
                "mod_database_seed_plan": seed_plan,
                "postgresql_summary": {"database_name": "", "host_port": "", "redacted_url": ""},
                "database_url": None,
                "current_db": None,
                "current_db_name": "postgresql",
                "message": str(e),
                "production_db": {"path": None, "exists": False, "note": str(e)},
                "test_db": {
                    "path": None,
                    "exists": False,
                    "note": "门禁关闭，未解析 DATABASE_URL",
                },
            }
        raise
    mode = resolve_mode()
    summary = postgresql_connection_summary(url)
    out = {
        "mode": mode,
        "backend": "postgresql",
        "database_url": summary["redacted_url"],
        "current_db": summary["redacted_url"],
        "current_db_name": "postgresql",
        "postgresql_summary": summary,
        "production_db": {"path": None, "exists": True, "note": "使用 DATABASE_URL"},
        "test_db": {
            "path": None,
            "exists": False,
            "note": "PostgreSQL 下不创建独立 products_test.db 文件",
        },
    }
    if gate.get("required_mod_ids"):
        out["mod_database_gate"] = gate
    try:
        from backend.shell.mod_database_gate import mod_database_seed_plan_dict

        out["mod_database_seed_plan"] = mod_database_seed_plan_dict()
    except Exception as e:
        logger.warning("mod_database_seed_plan 构建失败: %s", e)
        out["mod_database_seed_plan"] = {"mods": [], "error": str(e)}
    return out


def switch_to_test_mode() -> dict:
    return set_mode("test")


def switch_to_production_mode() -> dict:
    result = set_mode("production")
    if "error" not in result and not database_url_is_postgresql():
        reset_result = reset_test_db()
        result["reset_test_db"] = reset_result.get("status") == "reset"
    return result
