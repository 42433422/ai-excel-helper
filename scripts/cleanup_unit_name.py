#!/usr/bin/env python3
"""
从主库删除指定「购买单位/客户名」在 products.unit 与 purchase_units.unit_name 上的数据，
与后端删除客户时的规范化规则一致（全角空格、NBSP、Tab）。

用法（在仓库根目录）:
  python scripts/cleanup_unit_name.py
  python scripts/cleanup_unit_name.py 七彩乐园
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _pg_norm(col_sql: str) -> str:
    return (
        f"lower(btrim(replace(replace(replace(coalesce({col_sql}, ''), CHR(12288), ' '), "
        f"CHR(160), ' '), CHR(9), ' ')))"
    )


def cleanup_postgresql(name: str) -> tuple[int, int]:
    from sqlalchemy import create_engine, inspect, text

    from backend.database import get_database_url
    n = (name or "").strip()
    url = get_database_url()
    # 独立短连接，避免占用全局引擎；connect_timeout 防止本机未起 PG 时无限挂起
    eng = create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 8},
    )
    insp = inspect(eng)
    prod_del = 0
    pu_del = 0
    try:
        with eng.begin() as conn:
            if "products" in insp.get_table_names() and "unit" in {
                c["name"] for c in insp.get_columns("products")
            }:
                col = _pg_norm("CAST(unit AS TEXT)")
                prm = _pg_norm("CAST(:u AS TEXT)")
                r = conn.execute(text(f"DELETE FROM products WHERE {col} = {prm}"), {"u": n})
                prod_del = int(r.rowcount or 0)
            if "purchase_units" in insp.get_table_names() and "unit_name" in {
                c["name"] for c in insp.get_columns("purchase_units")
            }:
                col = _pg_norm("CAST(unit_name AS TEXT)")
                prm = _pg_norm("CAST(:u AS TEXT)")
                r = conn.execute(text(f"DELETE FROM purchase_units WHERE {col} = {prm}"), {"u": n})
                pu_del = int(r.rowcount or 0)
    finally:
        eng.dispose()
    return prod_del, pu_del


def main() -> None:
    parser = argparse.ArgumentParser(description="按购买单位/客户名清理 products 与 purchase_units")
    parser.add_argument("name", nargs="?", default="七彩乐园", help="要清理的单位名称（默认：七彩乐园）")
    parser.add_argument("--dry-run", action="store_true", help="仅打印将要使用的库类型，不执行删除")
    args = parser.parse_args()

    from backend.database import get_database_url, redact_database_url

    url = get_database_url()
    print("DATABASE_URL:", redact_database_url(url))

    if args.dry_run:
        print("dry-run：未执行删除")
        return

    p, u = cleanup_postgresql(args.name)
    print(f"PostgreSQL：已删除 products 行数={p}，purchase_units 行数={u}（匹配「{args.name}」）")


if __name__ == "__main__":
    main()
