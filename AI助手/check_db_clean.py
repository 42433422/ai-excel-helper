#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查数据库是否已清理"""
import sqlite3

db_path = "products.db"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    tables = ['purchase_units', 'products', 'customer_products']
    for t in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {t}")
        count = cursor.fetchone()[0]
        print(f"{t}: {count} 条记录")
    conn.close()
    print("\n✅ 数据库检查完成")
except Exception as e:
    print(f"❌ 检查失败: {e}")
