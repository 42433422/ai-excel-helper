#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解析 XCAGI/.env 的 DATABASE_URL，并打印当前库标识 + purchase_units 摘要。
用于确认「奇士美 / 百木鼎」等业务数据是否在本机 PostgreSQL 的 xcagi 库，或是否误连 SQLite。

用法（在仓库根 E:\\FHD）:
  python scripts/xcagi_inspect_database.py
  python scripts/xcagi_inspect_database.py --needle 百木鼎
"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_database_url_from_env_file() -> str:
    env_path = _repo_root() / "XCAGI" / ".env"
    if not env_path.is_file():
        return (os.environ.get("DATABASE_URL") or "").strip()
    raw = env_path.read_text(encoding="utf-8", errors="replace")
    for line in raw.splitlines():
        m = re.match(r"^\s*DATABASE_URL\s*=\s*(.+?)\s*$", line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    return (os.environ.get("DATABASE_URL") or "").strip()


def _redact_url(url: str) -> str:
    try:
        p = urlparse(url.replace("+psycopg", "").replace("+psycopg2", ""))
        if p.password:
            netloc = f"{p.username or ''}:***@{p.hostname or ''}"
            if p.port:
                netloc += f":{p.port}"
            return p._replace(netloc=netloc).geturl()
    except Exception:
        pass
    return url


def _inspect_sqlite(path: Path, needle: str) -> int:
    print(
        f"SQLite file: {path} (exists={path.is_file()}, size={path.stat().st_size if path.is_file() else 0})"
    )
    if not path.is_file():
        return 1
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('purchase_units','products','customers')"
        )
        print("tables:", [r[0] for r in cur.fetchall()])
        try:
            cur.execute("SELECT COUNT(*) FROM purchase_units")
            print("purchase_units count:", cur.fetchone()[0])
            cur.execute(
                "SELECT id, unit_name, IFNULL(xcagi_mod_id,'') FROM purchase_units ORDER BY id LIMIT 30"
            )
            print("purchase_units sample:", cur.fetchall())
        except sqlite3.Error as e:
            print("purchase_units:", e)
        if needle:
            try:
                cur.execute(
                    "SELECT id, unit_name FROM purchase_units WHERE unit_name LIKE ? LIMIT 10",
                    (f"%{needle}%",),
                )
                print(f"purchase_units LIKE %{needle}%:", cur.fetchall())
            except sqlite3.Error:
                pass
    finally:
        conn.close()
    return 0


def _inspect_postgres(url: str, needle: str) -> int:
    try:
        import psycopg
    except ImportError:
        print("需要 psycopg：pip install psycopg[binary]", file=sys.stderr)
        return 2
    conn_s = url.replace("+psycopg", "").replace("+psycopg2", "")
    print("PostgreSQL:", _redact_url(url))
    try:
        conn = psycopg.connect(conn_s, connect_timeout=8)
    except Exception as e:
        print("连接失败:", e, file=sys.stderr)
        return 3
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), inet_server_addr(), inet_server_port()")
            print("current_database / host / port:", cur.fetchone())
            cur.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name IN ('purchase_units','products','customers')
                ORDER BY 1
                """
            )
            print("core tables:", [r[0] for r in cur.fetchall()])
            cur.execute("SELECT COUNT(*) FROM purchase_units")
            print("purchase_units count:", cur.fetchone()[0])
            cur.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema='public' AND table_name='purchase_units'
                """
            )
            pu_cols = {r[0] for r in cur.fetchall()}
            mod_col = "xcagi_mod_id" if "xcagi_mod_id" in pu_cols else None
            if mod_col:
                cur.execute(
                    f"""
                    SELECT id, unit_name, {mod_col} FROM purchase_units
                    ORDER BY COALESCE({mod_col},''), id
                    LIMIT 40
                    """
                )
            else:
                print(
                    "注意: purchase_units 无 xcagi_mod_id 列，请执行 scripts/pg_init_xcagi_core.sql"
                )
                cur.execute(
                    """
                    SELECT id, unit_name FROM purchase_units
                    ORDER BY id
                    LIMIT 40
                    """
                )
            print("purchase_units sample:", cur.fetchall())
            if needle:
                if mod_col:
                    cur.execute(
                        f"SELECT id, unit_name, {mod_col} FROM purchase_units WHERE unit_name ILIKE %s LIMIT 20",
                        (f"%{needle}%",),
                    )
                else:
                    cur.execute(
                        "SELECT id, unit_name FROM purchase_units WHERE unit_name ILIKE %s LIMIT 20",
                        (f"%{needle}%",),
                    )
                print(f"purchase_units ILIKE %{needle}%:", cur.fetchall())
                for tbl, cols in (
                    ("customers", ("customer_name", "name")),
                    ("products", ("name", "description")),
                ):
                    cur.execute(
                        "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s",
                        (tbl,),
                    )
                    have = {r[0] for r in cur.fetchall()}
                    for c in cols:
                        if c not in have:
                            continue
                        cur.execute(
                            f'SELECT id, "{c}" FROM {tbl} WHERE CAST("{c}" AS TEXT) ILIKE %s LIMIT 5',
                            (f"%{needle}%",),
                        )
                        rows = cur.fetchall()
                        if rows:
                            print(f"{tbl}.{c} ILIKE:", rows)
    finally:
        conn.close()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Inspect XCAGI DATABASE_URL target (PG or SQLite).")
    ap.add_argument("--needle", default="", help="Optional substring e.g. company name to search")
    args = ap.parse_args()
    needle = (args.needle or "").strip()

    url = (os.environ.get("DATABASE_URL") or "").strip() or _load_database_url_from_env_file()
    if not url:
        print("未找到 DATABASE_URL（请设置环境变量或配置 XCAGI/.env）", file=sys.stderr)
        return 1

    print("Resolved DATABASE_URL:", _redact_url(url))

    if url.lower().startswith("sqlite"):
        # sqlite:///C:/path or sqlite:////path
        path_part = url.split("sqlite:///", 1)[-1].split("?", 1)[0]
        path_part = unquote(path_part)
        if (
            os.name == "nt"
            and path_part.startswith("/")
            and len(path_part) > 2
            and path_part[2] == ":"
        ):
            path_part = path_part[1:]
        db_path = Path(path_part)
        if not db_path.is_absolute():
            db_path = (_repo_root() / db_path).resolve()
        return _inspect_sqlite(db_path, needle)

    if "postgresql" in url.lower():
        return _inspect_postgres(url, needle)

    print("不支持的 DATABASE_URL 协议", file=sys.stderr)
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
