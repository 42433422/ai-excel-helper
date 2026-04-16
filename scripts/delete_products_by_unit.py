#!/usr/bin/env python3
"""按购买单位（products.unit）删除产品；需已配置 DATABASE_URL（PostgreSQL）。"""
from __future__ import annotations

import argparse
import os
import sys

# 仓库根：…/FHD/scripts/ → 父目录加入 path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def main() -> int:
    p = argparse.ArgumentParser(description="删除指定购买单位下的全部产品行")
    p.add_argument("unit_name", help="与 products.unit 一致的购买单位名称，例如：七彩乐园")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="只统计将要删除的行数，不执行 DELETE",
    )
    args = p.parse_args()
    unit = (args.unit_name or "").strip()
    if not unit:
        print("unit_name 不能为空", file=sys.stderr)
        return 2

    from sqlalchemy import inspect, text

    from backend.database import dispose_sync_engine, get_sync_engine, get_database_url
    from backend.routers.xcagi_compat import (
        _customer_pg_products_has_unit,
        _pg_expr_norm_unit,
    )

    _ = get_database_url()
    eng = get_sync_engine()
    insp = inspect(eng)
    if not _customer_pg_products_has_unit(insp):
        print("当前库无 products.unit 列，退出。", file=sys.stderr)
        return 1

    col = _pg_expr_norm_unit("CAST(unit AS TEXT)")
    prm = _pg_expr_norm_unit("CAST(:u AS TEXT)")
    with eng.connect() as conn:
        cnt = conn.execute(
            text(f"SELECT COUNT(*) FROM products WHERE {col} = {prm}"),
            {"u": unit},
        ).scalar()
    n = int(cnt or 0)
    print(f"匹配「{unit}」的产品行数: {n}")
    if args.dry_run or n == 0:
        dispose_sync_engine()
        return 0

    from backend.routers.xcagi_compat import _products_delete_by_unit_pg

    deleted = _products_delete_by_unit_pg(eng, unit)
    dispose_sync_engine()
    print(f"已删除: {deleted} 行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
