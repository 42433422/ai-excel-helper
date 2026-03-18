#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库中是否有重复的产品
"""

import sqlite3

db_path = "products.db"

print("=== 检查数据库产品重复情况 ===")

# 连接数据库
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. 检查产品总数
cursor.execute("SELECT COUNT(*) FROM products WHERE is_active = 1")
total_products = cursor.fetchone()[0]
print(f"总产品数量: {total_products}")

# 2. 检查唯一产品型号数量
cursor.execute("SELECT COUNT(DISTINCT model_number) FROM products WHERE is_active = 1 AND model_number IS NOT NULL AND model_number != ''")
unique_models = cursor.fetchone()[0]
print(f"唯一产品型号数量: {unique_models}")

# 3. 检查重复的产品型号
cursor.execute("""
    SELECT model_number, COUNT(*) as count 
    FROM products 
    WHERE is_active = 1 AND model_number IS NOT NULL AND model_number != ''
    GROUP BY model_number 
    HAVING COUNT(*) > 1 
    ORDER BY count DESC
""")
duplicates = cursor.fetchall()

print(f"重复产品型号数量: {len(duplicates)}")
if duplicates:
    print("前10个重复的产品型号:")
    for model, count in duplicates[:10]:
        print(f"  - {model}: {count}个重复")

# 4. 检查产品型号分布
cursor.execute("""
    SELECT model_number, name, COUNT(*) as count 
    FROM products 
    WHERE is_active = 1 
    GROUP BY model_number, name 
    ORDER BY count DESC
""")
product_distribution = cursor.fetchall()

print(f"\n产品分布情况 (前20个):")
for model, name, count in product_distribution[:20]:
    print(f"  - {model}: {name} ({count}个)")

# 5. 检查蕊芯相关产品
cursor.execute("""
    SELECT model_number, name, COUNT(*) as count 
    FROM products 
    WHERE is_active = 1 AND (name LIKE '%蕊芯%' OR model_number LIKE '%RX%')
    GROUP BY model_number, name 
    ORDER BY count DESC
""")
ruixin_products = cursor.fetchall()

print(f"\n蕊芯相关产品数量: {len(ruixin_products)}")
if ruixin_products:
    print("前10个蕊芯相关产品:")
    for model, name, count in ruixin_products[:10]:
        print(f"  - {model}: {name} ({count}个)")

# 关闭连接
conn.close()
print("\n=== 检查完成 ===")
