"""Desktop data backup and migration entry points."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

from app.utils.time import utc_now_naive

from .paths import configure_desktop_environment, ensure_desktop_dirs


def backup_database(
    data_dir: str | os.PathLike[str] | None = None, version: str = "unknown"
) -> Path | None:
    dirs = ensure_desktop_dirs(data_dir)
    db = dirs["data"] / "xcagi.db"
    if not db.exists():
        return None
    stamp = utc_now_naive().strftime("%Y%m%d%H%M%S")
    target = dirs["backups"] / f"xcagi-{version}-{stamp}.db"
    shutil.copy2(db, target)
    return target


def run_alembic_upgrade(
    data_dir: str | os.PathLike[str] | None = None, version: str = "head"
) -> None:
    configure_desktop_environment(data_dir)
    if _should_bootstrap_sqlite(data_dir):
        bootstrap_sqlite_schema(data_dir)
        subprocess.run([sys.executable, "-m", "alembic", "stamp", "head"], check=True)
        return
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", version], check=True)


def _should_bootstrap_sqlite(data_dir: str | os.PathLike[str] | None = None) -> bool:
    db_path = ensure_desktop_dirs(data_dir)["data"] / "xcagi.db"
    if not db_path.exists() or db_path.stat().st_size == 0:
        return True
    try:
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                "select name from sqlite_master where type='table' and name not like 'sqlite_%'"
            ).fetchall()
        return not rows
    except sqlite3.DatabaseError:
        return True


def bootstrap_sqlite_schema(data_dir: str | os.PathLike[str] | None = None) -> None:
    configure_desktop_environment(data_dir)
    # Import model modules so Base.metadata contains the full schema.
    import app.db.models  # noqa: F401
    from app.db import dispose_and_recreate_engine, engine
    from app.db.base import Base

    dispose_and_recreate_engine()
    Base.metadata.create_all(bind=engine)


def export_config(data_dir: str | os.PathLike[str] | None = None) -> dict[str, str]:
    dirs = ensure_desktop_dirs(data_dir)
    config = {
        "data_dir": str(dirs["root"]),
        "database": str(dirs["data"] / "xcagi.db"),
        "mods": str(dirs["mods"]),
        "models": str(dirs["models"]),
    }
    return config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="XCAGI desktop migration helper")
    parser.add_argument("--data-dir", default=os.environ.get("XCAGI_DATA_DIR"))
    parser.add_argument("--backup", action="store_true")
    parser.add_argument("--upgrade", default="")
    parser.add_argument("--export-config", action="store_true")
    parser.add_argument("--version", default=os.environ.get("XCAGI_VERSION", "unknown"))
    args = parser.parse_args(argv)

    configure_desktop_environment(args.data_dir)
    if args.backup:
        backup = backup_database(args.data_dir, args.version)
        if backup:
            print(str(backup))
    if args.upgrade:
        run_alembic_upgrade(args.data_dir, args.upgrade)
    if args.export_config:
        print(json.dumps(export_config(args.data_dir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
