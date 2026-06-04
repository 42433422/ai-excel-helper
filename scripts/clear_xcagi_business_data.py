#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清空 XCAGI / FHD 业务库中与「产品、购买单位、客户、出货」等相关数据，便于重新上传。

读取环境变量 DATABASE_URL（可先在本仓库根或 XCAGI 目录放 .env，由 dotenv 加载）。

模式：
  --mod <id>     仅删除 xcagi_mod_id = <id> 的行（表无该列则跳过）。
  --also-null    与 --mod 合用：同时删除 xcagi_mod_id IS NULL 的行（谨慎）。
  --truncate-core  清空核心表全部行（所有扩展包一起清空；PostgreSQL 用 TRUNCATE … CASCADE，
                  SQLite 用 DELETE）。涉及表（存在才处理）：
                  products, purchase_units, customers, shipment_records

示例：
  python scripts/clear_xcagi_business_data.py --mod sz-qsm-pro
  python scripts/clear_xcagi_business_data.py --truncate-core

说明：若你启用了 XCAGI_MOD_ISOLATED_DATABASES 或单独映射了库 URL，请确认 DATABASE_URL
指向你要清空的那一套库（例如 xcagi__sz_qsm_pro），否则清的是「基库」而不是扩展库。
"""
from __future__ import annotations

import argparse
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for name in (".env",):
        p = os.path.join(_ROOT, name)
        if os.path.isfile(p):
            load_dotenv(p)
    xc = os.path.join(_ROOT, "XCAGI", ".env")
    if os.path.isfile(xc):
        load_dotenv(xc)


def _tables(conn, dialect: str) -> set[str]:
    from sqlalchemy import inspect

    return set(inspect(conn).get_table_names())


def _has_column(conn, table: str, col: str) -> bool:
    from sqlalchemy import inspect

    try:
        cols = {c["name"] for c in inspect(conn).get_columns(table)}
    except Exception:
        return False
    return col in cols


def _is_sqlite(url: str) -> bool:
    return (url or "").strip().lower().startswith("sqlite")


def main() -> int:
    _load_dotenv()
    ap = argparse.ArgumentParser(description="Clear XCAGI business rows for re-import.")
    ap.add_argument("--mod", help="Only delete rows with xcagi_mod_id = this (e.g. sz-qsm-pro)")
    ap.add_argument(
        "--also-null",
        action="store_true",
        help="With --mod: also delete rows where xcagi_mod_id IS NULL",
    )
    ap.add_argument(
        "--truncate-core",
        action="store_true",
        help="Truncate/delete all rows in products, purchase_units, customers, shipment_records",
    )
    args = ap.parse_args()
    if bool(args.mod) == bool(args.truncate_core):
        print("Specify exactly one of: --mod <id>  OR  --truncate-core", file=sys.stderr)
        return 2

    url = (os.environ.get("DATABASE_URL") or "").strip()
    if not url:
        print("ERROR: DATABASE_URL is not set.", file=sys.stderr)
        return 1

    from sqlalchemy import create_engine, text

    engine = create_engine(url, future=True)
    dialect = engine.url.get_backend_name()

    mod_tables = ("products", "purchase_units", "customers")
    core_tables = ("products", "purchase_units", "customers", "shipment_records")

    with engine.connect() as conn:
        names = _tables(conn, dialect)
        if args.truncate_core:
            todo = [t for t in core_tables if t in names]
            if not todo:
                print("No core tables found; nothing to do.")
                return 0
            if dialect == "postgresql":
                stmt = (
                    "TRUNCATE TABLE "
                    + ", ".join(f'"{t}"' for t in todo)
                    + " RESTART IDENTITY CASCADE"
                )
                conn.execute(text(stmt))
            else:
                for t in todo:
                    conn.execute(
                        text(f'DELETE FROM "{t}"' if dialect == "sqlite" else f"DELETE FROM {t}")
                    )
            conn.commit()
            print(
                "OK:",
                "truncated" if dialect == "postgresql" else "deleted all rows in",
                ", ".join(todo),
            )
            return 0

        # --mod
        mid = (args.mod or "").strip()
        if not mid:
            print("ERROR: empty --mod", file=sys.stderr)
            return 2
        deleted: dict[str, int] = {}
        for table in mod_tables:
            if table not in names:
                continue
            if not _has_column(conn, table, "xcagi_mod_id"):
                print(f"SKIP {table}: no xcagi_mod_id (run scripts/pg_init_xcagi_core.sql if PG)")
                continue
            if args.also_null:
                r = conn.execute(
                    text(f"DELETE FROM {table} WHERE xcagi_mod_id = :m OR xcagi_mod_id IS NULL"),
                    {"m": mid},
                )
            else:
                r = conn.execute(
                    text(f"DELETE FROM {table} WHERE xcagi_mod_id = :m"),
                    {"m": mid},
                )
            deleted[table] = r.rowcount or 0
        conn.commit()
        if not deleted:
            print("No deletions performed (tables missing or no xcagi_mod_id).")
            return 1
        print("OK deleted rows:", deleted)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
