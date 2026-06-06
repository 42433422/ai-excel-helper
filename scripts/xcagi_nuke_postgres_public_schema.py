#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
危险操作：清空当前 DATABASE_URL 指向的 PostgreSQL 数据库中的 **public** 架构（DROP SCHEMA … CASCADE），
相当于删除该库内几乎所有业务表与数据；随后重建 public、恢复 pgvector 扩展。

本仓库里的自动化/助手 **从未** 替你执行此脚本；只有你本地手动运行且 export 确认变量后才会生效。

前置：
  - DATABASE_URL 指向你要清空的那个 PostgreSQL **database**（不是整个集群）。
  - 连接用户须有 DROP/CREATE SCHEMA 权限（一般为库 owner）。

用法（在 E:\\FHD 下）:
  set XCAGI_CONFIRM_NUKE_DATABASE=I_UNDERSTAND_ALL_DATA_WILL_BE_DESTROYED
  set XCAGI_CONFIRM_NUKE_DATABASE_URL_HOST=127.0.0.1
  python scripts/xcagi_nuke_postgres_public_schema.py

第二项必须与 URL 中的 host 一致（防止误连生产），例如 host 为 127.0.0.1 或 localhost。

完成后请在本机执行（XCAGI 目录）:
  python scripts/bootstrap_postgres.py
  python -m alembic upgrade head
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

REQUIRED_FLAG = "I_UNDERSTAND_ALL_DATA_WILL_BE_DESTROYED"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_database_url() -> str:
    env_path = _repo_root() / "XCAGI" / ".env"
    if env_path.is_file():
        raw = env_path.read_text(encoding="utf-8", errors="replace")
        for line in raw.splitlines():
            m = re.match(r"^\s*DATABASE_URL\s*=\s*(.+?)\s*$", line)
            if m:
                return m.group(1).strip().strip('"').strip("'")
    return (os.environ.get("DATABASE_URL") or "").strip()


def main() -> int:
    flag = (os.environ.get("XCAGI_CONFIRM_NUKE_DATABASE") or "").strip()
    if flag != REQUIRED_FLAG:
        print(
            "拒绝执行：请设置环境变量\n"
            f"  XCAGI_CONFIRM_NUKE_DATABASE={REQUIRED_FLAG}\n"
            "并设置 XCAGI_CONFIRM_NUKE_DATABASE_URL_HOST 为 DATABASE_URL 中的主机名。",
            file=sys.stderr,
        )
        return 1

    url = (os.environ.get("DATABASE_URL") or "").strip() or _load_database_url()
    if not url or "postgresql" not in url.lower():
        print("DATABASE_URL 必须是 PostgreSQL。", file=sys.stderr)
        return 2

    parsed = urlparse(url.replace("+psycopg", "").replace("+psycopg2", ""))
    host = (parsed.hostname or "").strip()
    expected_host = (os.environ.get("XCAGI_CONFIRM_NUKE_DATABASE_URL_HOST") or "").strip()
    if not expected_host or expected_host.lower() != host.lower():
        print(
            f"拒绝执行：URL host 为 {host!r}，但 XCAGI_CONFIRM_NUKE_DATABASE_URL_HOST={expected_host!r} 不匹配。",
            file=sys.stderr,
        )
        return 3

    try:
        import psycopg
        from psycopg import sql
    except ImportError:
        print("需要 psycopg：pip install psycopg[binary]", file=sys.stderr)
        return 4

    conn_s = url.replace("+psycopg", "").replace("+psycopg2", "")
    print("即将 DROP SCHEMA public CASCADE，数据库:", parsed.path or "", "host:", host)
    try:
        conn = psycopg.connect(conn_s, connect_timeout=15, autocommit=True)
    except Exception as e:
        print("连接失败:", e, file=sys.stderr)
        return 5

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT current_user, current_database()")
            role, dbname = cur.fetchone()
            print("current_user:", role, "database:", dbname)
            cur.execute(sql.SQL("DROP SCHEMA IF EXISTS public CASCADE"))
            cur.execute(sql.SQL("CREATE SCHEMA public"))
            cur.execute(sql.SQL("GRANT ALL ON SCHEMA public TO {}").format(sql.Identifier(role)))
            cur.execute(sql.SQL("GRANT ALL ON SCHEMA public TO PUBLIC"))
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        print("OK: public 已重建，vector 扩展已确保存在。")
        print("下一步（在 XCAGI 目录）: python scripts/bootstrap_postgres.py  # 若已执行可省略")
        print("然后: cd XCAGI && python -m alembic upgrade head")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
