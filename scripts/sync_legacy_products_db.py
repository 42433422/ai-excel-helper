#!/usr/bin/env python3
"""将历史 products.db 中的 purchase_units / products 同步到桌面 xcagi.db 与 PostgreSQL。"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
XCAGI_ROOT = PROJECT_ROOT / "XCAGI"
sys.path.insert(0, str(XCAGI_ROOT))


def _backup(path: Path) -> Path | None:
    if not path.is_file():
        return None
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = path.with_name(f"{path.name}.bak_{stamp}")
    shutil.copy2(path, dest)
    return dest


def _ensure_purchase_units_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS purchase_units (
            id INTEGER PRIMARY KEY,
            unit_name VARCHAR NOT NULL,
            contact_person VARCHAR,
            contact_phone VARCHAR,
            address VARCHAR,
            discount_rate FLOAT,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME,
            updated_at DATETIME
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_purchase_units_unit_name ON purchase_units(unit_name)"
    )


def _copy_table(
    src: sqlite3.Connection,
    dst: sqlite3.Connection,
    table: str,
    *,
    replace: bool = True,
) -> int:
    try:
        rows = src.execute(f'SELECT * FROM "{table}"').fetchall()
    except sqlite3.OperationalError:
        return 0
    if not rows:
        return 0
    cols = [d[0] for d in src.execute(f'SELECT * FROM "{table}" LIMIT 1').description]
    dst_cols = {r[1] for r in dst.execute(f'PRAGMA table_info("{table}")').fetchall()}
    use_cols = [c for c in cols if c in dst_cols]
    if not use_cols:
        return 0
    placeholders = ", ".join(["?"] * len(use_cols))
    col_sql = ", ".join(f'"{c}"' for c in use_cols)
    verb = "INSERT OR REPLACE" if replace else "INSERT OR IGNORE"
    sql = f'{verb} INTO "{table}" ({col_sql}) VALUES ({placeholders})'
    payload = [tuple(row[cols.index(c)] for c in use_cols) for row in rows]
    dst.executemany(sql, payload)
    return len(payload)


def sync_sqlite(source: Path, target: Path, *, backup: bool = True) -> dict[str, int]:
    if backup:
        _backup(target)
    src = sqlite3.connect(source)
    dst = sqlite3.connect(target)
    try:
        _ensure_purchase_units_table(dst)
        dst.commit()
        counts = {
            "purchase_units": _copy_table(src, dst, "purchase_units"),
            "products": _copy_table(src, dst, "products"),
        }
        dst.commit()
        return counts
    finally:
        src.close()
        dst.close()


def sync_postgres(source: Path, database_url: str) -> dict[str, int]:
    from sqlalchemy import Boolean, create_engine, inspect, text

    engine = create_engine(database_url, pool_pre_ping=True)
    insp = inspect(engine)
    if "purchase_units" not in insp.get_table_names():
        raise RuntimeError("PostgreSQL 缺少 purchase_units 表，请先执行 alembic upgrade head")

    src = sqlite3.connect(source)
    src.row_factory = sqlite3.Row
    counts: dict[str, int] = {}
    try:
        with engine.begin() as conn:
            for table in ("purchase_units", "products"):
                if table not in insp.get_table_names():
                    counts[table] = 0
                    continue
                rows = src.execute(f'SELECT * FROM "{table}"').fetchall()
                if not rows:
                    counts[table] = 0
                    continue
                src_cols = rows[0].keys()
                col_defs = inspect(conn).get_columns(table)
                tgt_cols = {c["name"] for c in col_defs}
                bool_cols = {c["name"] for c in col_defs if isinstance(c.get("type"), Boolean)}
                cols = [c for c in src_cols if c in tgt_cols]
                if not cols:
                    counts[table] = 0
                    continue
                conn.execute(text(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE'))
                placeholders = ", ".join(f":{c}" for c in cols)
                col_sql = ", ".join(f'"{c}"' for c in cols)
                stmt = text(f'INSERT INTO "{table}" ({col_sql}) VALUES ({placeholders})')
                payload = []
                for row in rows:
                    item = {}
                    for c in cols:
                        val = row[c]
                        if c in bool_cols and val is not None:
                            item[c] = bool(val)
                        else:
                            item[c] = val
                    payload.append(item)
                conn.execute(stmt, payload)
                counts[table] = len(payload)
    finally:
        src.close()
        engine.dispose()
    return counts


def patch_database_json(data_dir: Path, database_url: str) -> Path:
    cfg_path = data_dir / "config" / "database.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    profile = {
        "version": 1,
        "mode": "remote",
        "remote": {"enabled": True, "database_url": database_url},
    }
    if cfg_path.is_file():
        try:
            raw = json.loads(cfg_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                profile["version"] = raw.get("version", 1)
        except json.JSONDecodeError:
            pass
    cfg_path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return cfg_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        default=str(XCAGI_ROOT / "products.db"),
        help="历史 SQLite 母库（含 purchase_units）",
    )
    parser.add_argument(
        "--desktop-db",
        default=str(XCAGI_ROOT / "data" / "desktop-dev" / "data" / "xcagi.db"),
        help="桌面交付 xcagi.db",
    )
    parser.add_argument(
        "--postgres-url",
        default=os.environ.get(
            "DATABASE_URL", "postgresql+psycopg://xcagi:xcagi@127.0.0.1:5432/xcagi"
        ),
        help="Docker / 中心 PostgreSQL URL",
    )
    parser.add_argument(
        "--data-dir",
        default=str(XCAGI_ROOT / "data" / "desktop-dev"),
        help="桌面 data-dir（写入 database.json）",
    )
    parser.add_argument("--skip-postgres", action="store_true")
    parser.add_argument("--skip-desktop", action="store_true")
    parser.add_argument("--no-remote-profile", action="store_true")
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args()

    source = Path(args.source).resolve()
    if not source.is_file():
        print(f"ERROR: 源库不存在: {source}", file=sys.stderr)
        return 1

    if not args.skip_desktop:
        desktop_db = Path(args.desktop_db).resolve()
        desktop_db.parent.mkdir(parents=True, exist_ok=True)
        counts = sync_sqlite(source, desktop_db, backup=not args.no_backup)
        print(f"[desktop] {desktop_db}")
        for k, v in counts.items():
            print(f"  {k}: {v} rows")

    if not args.skip_postgres:
        url = (args.postgres_url or "").strip()
        if not url.startswith("postgresql"):
            print("WARN: 跳过 PostgreSQL（未配置 postgresql URL）")
        else:
            pg_counts = sync_postgres(source, url)
            print(f"[postgres] {url}")
            for k, v in pg_counts.items():
                print(f"  {k}: {v} rows")

    if not args.no_remote_profile:
        cfg = patch_database_json(Path(args.data_dir).resolve(), args.postgres_url)
        print(f"[profile] 已启用远程库: {cfg}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
