#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为每个扩展（Mod）在 PostgreSQL 上创建独立业务库，并启用 pgvector。

与 app.db / app.infrastructure.db.mod_database_url 中
XCAGI_MOD_ISOLATED_DATABASES=1 时的命名一致：
    {基库名}__{mod_id 规范化小写后缀}

策略：
- 默认以 ``taiyangniao-pro`` 作为「从基库克隆」的 Mod（``--clone-from-base``），承接当前基库数据：
  用 CREATE DATABASE ... WITH TEMPLATE <base> 克隆一份；这要求源库无其它连接。
- 其余 Mod 起空库，随后交给 migrate_mod_dbs.py 跑 alembic。
- 已存在的库一律 SKIP（幂等）。
- 每个新库都尝试 CREATE EXTENSION IF NOT EXISTS vector。

Mod 发现顺序：
    1. 环境变量 XCAGI_MOD_DATABASE_URLS 的 JSON 键
    2. 环境变量 XCAGI_MOD_IDS（逗号分隔）
    3. 扫 <repo>/mods/*/manifest.json 的 id 字段

用法（仓库根目录）：
    python scripts/bootstrap_mod_dbs.py

备份建议（先跑一次）：
    docker exec <pg_container> pg_dump -U xcagi xcagi > backup_xcagi.sql
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env")
except ImportError:
    pass


PRIMARY_CLONE_MOD_ID_DEFAULT = "taiyangniao-pro"
# 需完整 ERP/产品域表结构的 Mod：从基库 TEMPLATE 克隆（空库 + alembic 无法补齐 products 等历史表）
DEFAULT_CLONE_FROM_BASE_MOD_IDS = (
    PRIMARY_CLONE_MOD_ID_DEFAULT,
    "xcagi-erp-domain-bridge",
)


def _normalize_mod_file_suffix(mod_id: str) -> str:
    return (
        "".join(ch if ch.isalnum() else "_" for ch in str(mod_id or "").strip()).strip("_").lower()
    )


def _discover_mod_ids() -> list[str]:
    raw_json = (os.environ.get("XCAGI_MOD_DATABASE_URLS") or "").strip()
    if raw_json:
        try:
            obj = json.loads(raw_json)
            if isinstance(obj, dict):
                keys = [str(k).strip() for k in obj if str(k).strip()]
                if keys:
                    return sorted(set(keys))
        except json.JSONDecodeError:
            pass

    csv_ids = (os.environ.get("XCAGI_MOD_IDS") or "").strip()
    if csv_ids:
        return sorted({p.strip() for p in csv_ids.split(",") if p.strip()})

    mods_dir = _ROOT / "mods"
    if not mods_dir.is_dir():
        return []
    out: list[str] = []
    seen: set[str] = set()
    for child in sorted(mods_dir.iterdir()):
        if not child.is_dir():
            continue
        mf = child / "manifest.json"
        if not mf.is_file():
            continue
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        mid = str((data or {}).get("id") or "").strip()
        if mid and mid not in seen:
            seen.add(mid)
            out.append(mid)
    return out


def _maintenance_engine(base_url: str):
    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url

    u = make_url(base_url)
    if u.get_backend_name() != "postgresql":
        raise SystemExit("ERROR: DATABASE_URL must be PostgreSQL.")
    admin = u.set(database="postgres")
    return create_engine(admin, isolation_level="AUTOCOMMIT", future=True)


def _db_exists(conn, dbname: str) -> bool:
    from sqlalchemy import text

    row = conn.execute(
        text("SELECT 1 FROM pg_database WHERE datname = :n"),
        {"n": dbname},
    ).fetchone()
    return bool(row)


def _terminate_other_connections(conn, dbname: str) -> int:
    from sqlalchemy import text

    row = conn.execute(
        text(
            """
            SELECT COUNT(*) FROM (
                SELECT pg_terminate_backend(pid) AS ok
                FROM pg_stat_activity
                WHERE datname = :n AND pid <> pg_backend_pid()
            ) s WHERE ok
            """
        ),
        {"n": dbname},
    ).fetchone()
    return int(row[0] if row else 0)


def _create_db_from_template(conn, new_db: str, template_db: str, owner: str | None) -> None:
    from sqlalchemy import text

    terminated = _terminate_other_connections(conn, template_db)
    if terminated:
        print(f"  -> terminated {terminated} existing connection(s) on {template_db}")
    owner_clause = f' OWNER "{owner}"' if owner else ""
    conn.execute(text(f'CREATE DATABASE "{new_db}" WITH TEMPLATE "{template_db}"{owner_clause}'))


def _create_db_empty(conn, new_db: str, owner: str | None) -> None:
    from sqlalchemy import text

    owner_clause = f' OWNER "{owner}"' if owner else ""
    conn.execute(text(f'CREATE DATABASE "{new_db}"{owner_clause}'))


def _url_for_database(base_url_obj, dbname: str) -> str:
    return base_url_obj.set(database=dbname).render_as_string(hide_password=False)


def _parse_clone_mod_ids(raw: str) -> set[str]:
    s = str(raw or "").strip()
    if not s or s.lower() == "none":
        return set()
    return {p.strip() for p in s.split(",") if p.strip()}


def _drop_database(conn, dbname: str) -> None:
    from sqlalchemy import text

    _terminate_other_connections(conn, dbname)
    conn.execute(text(f'DROP DATABASE IF EXISTS "{dbname}"'))


def recreate_mod_database_from_base(mod_id: str, *, force: bool = True) -> bool:
    """删除并自基库 TEMPLATE 重建指定 Mod 库（修复空库迁移失败）。"""
    base_url = (os.environ.get("DATABASE_URL") or "").strip()
    if not base_url.startswith("postgresql") and not base_url.startswith("postgres"):
        return False
    suf = _normalize_mod_file_suffix(mod_id)
    if not suf:
        return False
    from sqlalchemy.engine import make_url

    base_u = make_url(base_url)
    base_db = (base_u.database or "xcagi").strip()
    dbn = f"{base_db}__{suf}"
    admin_engine = _maintenance_engine(base_url)
    with admin_engine.connect() as conn:
        if not _db_exists(conn, base_db):
            admin_engine.dispose()
            return False
        if _db_exists(conn, dbn):
            print(f"DROP {dbn}")
            _drop_database(conn, dbn)
        print(f"CLONE {base_db} -> {dbn}")
        _create_db_from_template(conn, dbn, base_db, base_u.username or None)
    admin_engine.dispose()
    mod_url = _url_for_database(base_u, dbn)
    _enable_pgvector(mod_url, dbn)
    return True


def _enable_pgvector(mod_url: str, dbname: str) -> None:
    from sqlalchemy import create_engine, text

    try:
        eng = create_engine(mod_url, isolation_level="AUTOCOMMIT", future=True)
        with eng.connect() as c:
            c.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        eng.dispose()
        print(f"  OK pgvector enabled: {dbname}")
    except Exception as exc:
        print(
            f"  WARN pgvector on {dbname} failed ({exc}). "
            f'Fix manually: psql "{mod_url}" -c "CREATE EXTENSION IF NOT EXISTS vector;"',
            file=sys.stderr,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--clone-from-base",
        default=",".join(DEFAULT_CLONE_FROM_BASE_MOD_IDS),
        help=(
            "用 WITH TEMPLATE <base> 克隆基库的 mod id 列表（逗号分隔）。"
            f"默认 {','.join(DEFAULT_CLONE_FROM_BASE_MOD_IDS)}；传 'none' 代表全部空建。"
        ),
    )
    parser.add_argument(
        "--recreate",
        default="",
        help="已存在时也 DROP 后自基库克隆（逗号分隔 mod id，如 xcagi-erp-domain-bridge）",
    )
    args = parser.parse_args(argv)

    base_url = (os.environ.get("DATABASE_URL") or "").strip()
    if not base_url:
        print("ERROR: DATABASE_URL is not set.", file=sys.stderr)
        return 1
    if not (base_url.startswith("postgresql") or base_url.startswith("postgres")):
        print("ERROR: DATABASE_URL must be a PostgreSQL URL.", file=sys.stderr)
        return 1

    mod_ids = _discover_mod_ids()
    if not mod_ids:
        print(
            "No mod ids found. Install manifests under mods/ or set "
            "XCAGI_MOD_DATABASE_URLS / XCAGI_MOD_IDS.",
            file=sys.stderr,
        )
        return 1

    from sqlalchemy.engine import make_url

    base_u = make_url(base_url)
    base_db = (base_u.database or "xcagi").strip()
    owner = base_u.username or None
    clone_mod_ids = _parse_clone_mod_ids(str(args.clone_from_base))
    recreate_mod_ids = _parse_clone_mod_ids(str(args.recreate or ""))

    print("============================================================")
    print(" bootstrap_mod_dbs.py")
    print(f" base database: {base_db}")
    print(f" mods:          {', '.join(mod_ids)}")
    print(f" clone targets: {', '.join(sorted(clone_mod_ids)) or '(none, all empty)'}")
    if recreate_mod_ids:
        print(f" recreate:      {', '.join(sorted(recreate_mod_ids))}")
    print("============================================================")
    print("WARNING: 建议先停掉后端 / 关闭所有连向基库的 psql，再继续。")
    print()

    admin_engine = _maintenance_engine(base_url)
    created: list[tuple[str, str]] = []  # [(mod_id, dbname)]

    with admin_engine.connect() as conn:
        if not _db_exists(conn, base_db):
            print(f"ERROR: base database {base_db} does not exist.", file=sys.stderr)
            admin_engine.dispose()
            return 1

        for mid in mod_ids:
            suf = _normalize_mod_file_suffix(mid)
            if not suf:
                continue
            dbn = f"{base_db}__{suf}"
            if _db_exists(conn, dbn):
                if mid in recreate_mod_ids:
                    print(f"RECREATE {dbn} from {base_db}")
                    _drop_database(conn, dbn)
                else:
                    print(f"SKIP exists: {dbn}")
                    continue
            if mid in clone_mod_ids:
                print(f"CLONE {base_db} -> {dbn}")
                _create_db_from_template(conn, dbn, base_db, owner)
            else:
                print(f"CREATE empty: {dbn}")
                _create_db_empty(conn, dbn, owner)
            created.append((mid, dbn))

    admin_engine.dispose()

    if not created:
        print("\nNo new database created; nothing to do.")
        return 0

    print("\n-- enabling pgvector on new databases --")
    for _mid, dbn in created:
        mod_url = _url_for_database(base_u, dbn)
        _enable_pgvector(mod_url, dbn)

    print("\nDone. Next:")
    print("  python scripts/migrate_mod_dbs.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
