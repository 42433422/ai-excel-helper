#!/usr/bin/env python3
"""
数据库合并脚本 - 将 customers.db 合并到 products.db

执行步骤：
1. 备份现有数据库
2. 从 customers.db 读取 purchase_units 数据
3. 将数据写入 products.db.purchase_units
4. 验证数据完整性
5. 可选：删除 customers.db

使用方式：
    python scripts/merge_databases.py --dry-run  # 预览
    python scripts/merge_databases.py             # 执行
    python scripts/merge_databases.py --rollback  # 回滚
"""

import argparse
import os
import shutil
import sqlite3
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app.db.init_db import get_db_path, get_customers_db_path


def backup_database(db_path: str) -> str:
    """备份数据库文件"""
    if not os.path.exists(db_path):
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    shutil.copy2(db_path, backup_path)
    print(f"  ✅ 备份: {backup_path}")
    return backup_path


def get_table_data(db_path: str, table_name: str) -> list:
    """获取表的所有数据"""
    if not os.path.exists(db_path):
        return []
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    columns = [description[0] for description in cursor.description]
    rows = cursor.fetchall()
    conn.close()
    return [dict(zip(columns, row)) for row in rows]


def merge_purchase_units(dry_run: bool = True) -> dict:
    """合并 purchase_units 表"""
    products_db = get_db_path("products.db")
    customers_db = get_customers_db_path()

    print("\n" + "=" * 60)
    print("数据库合并 - purchase_units 表")
    print("=" * 60)

    results = {
        "dry_run": dry_run,
        "backup_created": [],
        "records_copied": 0,
        "errors": []
    }

    if not os.path.exists(customers_db):
        print(f"\n⚠️ customers.db 不存在: {customers_db}")
        print("  跳过合并，purchase_units 可能已在 products.db 中")
        return results

    customers_data = get_table_data(customers_db, "purchase_units")
    print(f"\n📊 customers.db.purchase_units: {len(customers_data)} 条记录")

    if not dry_run:
        backup_created = backup_database(products_db)
        if backup_created:
            results["backup_created"].append(backup_created)

    products_data = get_table_data(products_db, "purchase_units")
    print(f"📊 products.db.purchase_units: {len(products_data)} 条记录")

    existing_names = {r["unit_name"] for r in products_data}

    to_merge = [r for r in customers_data if r.get("unit_name") not in existing_names]
    to_update = [r for r in customers_data if r.get("unit_name") in existing_names]

    print(f"\n📋 合并计划:")
    print(f"  - 新增: {len(to_merge)} 条")
    print(f"  - 更新: {len(to_update)} 条")

    if dry_run:
        print("\n🔍 预览 (dry-run，不执行实际更改):")
        for r in to_merge[:5]:
            print(f"  + {r.get('unit_name', 'N/A')}")
        if len(to_merge) > 5:
            print(f"  ... 还有 {len(to_merge) - 5} 条")
        for r in to_update[:3]:
            print(f"  ~ {r.get('unit_name', 'N/A')}")
        if len(to_update) > 3:
            print(f"  ... 还有 {len(to_update) - 3} 条")
        print("\n使用 --no-dry-run 执行实际合并")
        return results

    if not to_merge and not to_update:
        print("\n✅ 数据已是最新，无需合并")
        return results

    conn = sqlite3.connect(products_db)
    cursor = conn.cursor()

    try:
        for record in to_merge:
            cursor.execute("""
                INSERT INTO purchase_units (unit_name, contact_person, contact_phone, address, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("unit_name"),
                record.get("contact_person", ""),
                record.get("contact_phone", ""),
                record.get("address", ""),
                record.get("is_active", 1),
                record.get("created_at"),
                record.get("updated_at")
            ))
            results["records_copied"] += 1

        for record in to_update:
            cursor.execute("""
                UPDATE purchase_units
                SET contact_person = ?, contact_phone = ?, address = ?, is_active = ?, updated_at = ?
                WHERE unit_name = ?
            """, (
                record.get("contact_person", ""),
                record.get("contact_phone", ""),
                record.get("address", ""),
                record.get("is_active", 1),
                datetime.now().isoformat(),
                record.get("unit_name")
            ))

        conn.commit()
        print(f"\n✅ 成功合并 {results['records_copied']} 条记录")

    except Exception as e:
        conn.rollback()
        results["errors"].append(str(e))
        print(f"\n❌ 合并失败: {e}")

    finally:
        conn.close()

    return results


def verify_merge() -> dict:
    """验证合并结果"""
    products_db = get_db_path("products.db")
    customers_db = get_customers_db_path()

    results = {
        "products_db_exists": os.path.exists(products_db),
        "customers_db_exists": os.path.exists(customers_db),
        "products_purchase_units_count": 0,
        "customers_purchase_units_count": 0,
        "is_consistent": False
    }

    if os.path.exists(products_db):
        conn = sqlite3.connect(products_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM purchase_units")
        results["products_purchase_units_count"] = cursor.fetchone()[0]
        conn.close()

    if os.path.exists(customers_db):
        conn = sqlite3.connect(customers_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM purchase_units")
        results["customers_purchase_units_count"] = cursor.fetchone()[0]
        conn.close()

    results["is_consistent"] = (
        results["customers_purchase_units_count"] == 0 or
        results["products_purchase_units_count"] >=
        results["customers_purchase_units_count"]
    )

    return results


def main():
    parser = argparse.ArgumentParser(description="合并 customers.db 到 products.db")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不执行实际更改")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false", help="执行实际合并")
    parser.add_argument("--verify", action="store_true", help="验证合并结果")
    parser.add_argument("--cleanup", action="store_true", help="合并后删除 customers.db")

    args = parser.parse_args()

    if args.verify:
        print("\n🔍 验证合并结果...")
        result = verify_merge()
        print(f"\n📊 验证结果:")
        print(f"  products.db 存在: {result['products_db_exists']}")
        print(f"  products.db.purchase_units: {result['products_purchase_units_count']} 条")
        print(f"  customers.db 存在: {result['customers_db_exists']}")
        print(f"  customers.db.purchase_units: {result['customers_purchase_units_count']} 条")
        print(f"  数据一致性: {'✅' if result['is_consistent'] else '❌'}")
        return

    if args.dry_run:
        merge_purchase_units(dry_run=True)
        return

    results = merge_purchase_units(dry_run=False)

    if results["errors"]:
        print("\n⚠️ 合并过程中有错误:")
        for err in results["errors"]:
            print(f"  - {err}")
        return

    if args.cleanup and os.path.exists(get_customers_db_path()):
        print(f"\n🗑️  准备删除 customers.db...")
        backup_path = backup_database(get_customers_db_path())
        if backup_path:
            os.remove(get_customers_db_path())
            print(f"  ✅ 已删除: {get_customers_db_path()}")
            print(f"  📦 备份: {backup_path}")

    print("\n" + "=" * 60)
    print("验证合并结果...")
    verify_result = verify_merge()
    print(f"\n📊 products.db.purchase_units: {verify_result['products_purchase_units_count']} 条")
    print("✅ 合并完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
