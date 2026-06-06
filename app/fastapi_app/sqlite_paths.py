"""SQLite DATABASE_URL 解析。"""

from __future__ import annotations

import os


def is_sqlite_url(database_url: str | None) -> bool:
    return str(database_url or "").strip().startswith("sqlite")


def resolve_effective_database_url(config_url: str | None = None) -> str:
    """解析进程实际使用的 DATABASE_URL（优先运行时 env，避免 Config 类属性滞后）。"""
    try:
        from app.db import _get_database_url

        runtime = (_get_database_url() or "").strip()
    except Exception:
        runtime = ""
    cfg = str(config_url or "").strip()
    if runtime:
        return runtime
    return cfg


def sqlite_db_file_from_url(database_url: str | None) -> str | None:
    """从 DATABASE_URL 解析 SQLite 文件路径"""
    if not is_sqlite_url(database_url):
        return None
    raw = str(database_url).strip()
    prefix = "sqlite:///"
    if not raw.startswith(prefix):
        return None
    path = raw[len(prefix) :].split("?", 1)[0].strip()
    if not path or path == ":memory:":
        return None
    if os.name == "nt" and path.startswith("/") and len(path) > 2 and path[2] == ":":
        path = path[1:]
    return os.path.abspath(path.replace("/", os.sep))
