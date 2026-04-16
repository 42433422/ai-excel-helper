#!/usr/bin/env python3
"""
销售合同模板环境核对（计划「verify-pg-env」）：PostgreSQL 行、磁盘 送货单.xls、FHD_SALES_CONTRACT_TEMPLATE。

用法（仓库根目录）:
  .venv\\Scripts\\python scripts/verify_sales_contract_template_env.py

依赖 DATABASE_URL（或 conftest 同款默认 URL）；连不上则打印说明并退出码 1。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
DELIVERY = REPO / "424" / "document_templates" / "送货单.xls"


def main() -> int:
    env_tpl = (os.environ.get("FHD_SALES_CONTRACT_TEMPLATE") or "").strip()
    print("FHD_SALES_CONTRACT_TEMPLATE:", repr(env_tpl) if env_tpl else "(unset)")

    print("磁盘 送货单.xls:", DELIVERY, "->", "存在" if DELIVERY.is_file() else "缺失")

    try:
        from sqlalchemy import inspect, text

        from backend.database import get_sync_engine
        from backend.document_template_service import ROLE_SALES_CONTRACT
    except Exception as e:
        print("导入失败:", e)
        return 1

    try:
        eng = get_sync_engine()
        insp = inspect(eng)
        if "document_templates" not in insp.get_table_names():
            print("document_templates 表不存在")
            return 1
        with eng.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT slug, display_name, is_default, sort_order, storage_relpath, file_format "
                    "FROM document_templates WHERE role = :role AND is_active = true "
                    "ORDER BY (CASE WHEN storage_relpath ~* :pat THEN 0 ELSE 1 END), sort_order, display_name"
                ),
                {"role": ROLE_SALES_CONTRACT, "pat": r"\.(xls|xlsx|xlsm)$"},
            ).mappings().all()
    except Exception as e:
        print("PostgreSQL 查询失败:", e)
        print("请确认 DATABASE_URL 可达，或运行 scripts/docker-postgres-for-fhd.*")
        return 1

    if not rows:
        print("无 sales_contract_docx 行")
        return 1

    print("\n--- document_templates (sales_contract_docx) ---")
    for r in rows:
        print(
            f"  slug={r['slug']!r} default={r['is_default']} sort={r['sort_order']} "
            f"format={r['file_format']!r} path={r['storage_relpath']!r}"
        )

    defaults = [r for r in rows if r.get("is_default")]
    if len(defaults) > 1:
        print("\n警告: 多条 is_default=true，生成时按路径 Excel 优先与 sort 解析，建议只保留一条默认。")
    elif len(defaults) == 1:
        d0 = defaults[0]
        p = str(d0.get("storage_relpath") or "")
        low = p.lower()
        if not (low.endswith(".xls") or low.endswith(".xlsx") or low.endswith(".xlsm")):
            print("\n提示: 当前唯一默认行不是 Excel 路径；若期望 .xlsx 请改默认或放置 送货单.xls 后重启后端以跑 schema 同步。")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
