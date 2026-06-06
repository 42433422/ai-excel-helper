"""Database helpers for the desktop runtime."""

from __future__ import annotations

import os
from pathlib import Path

from .paths import ensure_desktop_dirs, sqlite_database_url


def configure_sqlite_defaults(data_dir: str | os.PathLike[str] | None = None) -> str:
    """Return and export the SQLite URL used by desktop mode."""

    dirs = ensure_desktop_dirs(data_dir)
    url = sqlite_database_url(dirs["root"])
    os.environ["DATABASE_URL"] = os.environ.get("XCAGI_DESKTOP_DATABASE_URL") or url
    os.environ["VECTOR_DB_URL"] = (
        os.environ.get("XCAGI_DESKTOP_VECTOR_DB_URL") or os.environ["DATABASE_URL"]
    )
    os.environ.setdefault("DATABASE_PATH", str(dirs["data"]))
    return os.environ["DATABASE_URL"]


def database_file(data_dir: str | os.PathLike[str] | None = None) -> Path:
    return ensure_desktop_dirs(data_dir)["data"] / "xcagi.db"
