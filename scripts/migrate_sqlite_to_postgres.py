from __future__ import annotations

import argparse
import os
import sqlite3
from typing import List

from sqlalchemy import Boolean, create_engine, inspect, text

EXCLUDED_TABLES = {"sqlite_sequence", "alembic_version"}


def _sqlite_tables(conn: sqlite3.Connection) -> List[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    return [row[0] for row in rows if row[0] not in EXCLUDED_TABLES]


def _copy_table(sqlite_conn: sqlite3.Connection, pg_engine, table_name: str) -> int:
    rows = sqlite_conn.execute(f'SELECT * FROM "{table_name}"').fetchall()
    if not rows:
        return 0
    source_columns = [desc[0] for desc in sqlite_conn.execute(f'SELECT * FROM "{table_name}" LIMIT 1').description]

    payload = []
    for row in rows:
        item = {}
        for idx, col in enumerate(source_columns):
            item[col] = row[idx]
        payload.append(item)

    with pg_engine.begin() as conn:
        exists = conn.execute(
            text("SELECT to_regclass(:table_name)"),
            {"table_name": table_name},
        ).scalar()
        if not exists:
            print(f"[migrate] {table_name}: skipped (target table not found)")
            return 0
        target_column_defs = inspect(conn).get_columns(table_name)
        target_columns = {col["name"] for col in target_column_defs}
        bool_columns = {
            col["name"]
            for col in target_column_defs
            if isinstance(col.get("type"), Boolean)
        }
        columns = [col for col in source_columns if col in target_columns]
        if not columns:
            print(f"[migrate] {table_name}: skipped (no common columns)")
            return 0
        placeholders = ", ".join([f":{c}" for c in columns])
        col_sql = ", ".join([f'"{c}"' for c in columns])
        stmt = text(f'INSERT INTO "{table_name}" ({col_sql}) VALUES ({placeholders})')
        filtered_payload = []
        for row in payload:
            converted = {}
            for k in columns:
                value = row.get(k)
                if k in bool_columns and value is not None:
                    converted[k] = bool(value)
                else:
                    converted[k] = value
            filtered_payload.append(converted)
        conn.execute(text(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE'))
        conn.execute(stmt, filtered_payload)
    return len(filtered_payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate SQLite data to PostgreSQL")
    parser.add_argument(
        "--sqlite-path",
        default=os.environ.get("SQLITE_PATH", "data/products.db"),
        help="Path to SQLite database file",
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", ""),
        help="PostgreSQL DATABASE_URL",
    )
    args = parser.parse_args()

    if not args.database_url:
        raise ValueError("DATABASE_URL is required")
    if not os.path.exists(args.sqlite_path):
        raise FileNotFoundError(f"SQLite file not found: {args.sqlite_path}")

    sqlite_conn = sqlite3.connect(args.sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    pg_engine = create_engine(args.database_url, pool_pre_ping=True)
    try:
        total = 0
        for table in _sqlite_tables(sqlite_conn):
            try:
                copied = _copy_table(sqlite_conn, pg_engine, table)
                total += copied
                print(f"[migrate] {table}: {copied} rows")
            except Exception as exc:
                print(f"[migrate] {table}: skipped ({exc})")
        print(f"[migrate] done, total rows copied: {total}")
    finally:
        sqlite_conn.close()
        pg_engine.dispose()


if __name__ == "__main__":
    main()
