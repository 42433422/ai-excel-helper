#!/usr/bin/env python3
import sqlite3

# 检查七彩乐园数据库
conn = sqlite3.connect('unit_databases/七彩乐园.db')
cursor = conn.cursor()

print("=== 七彩乐园数据库中的产品 ===")
cursor.execute("SELECT * FROM products WHERE name LIKE '%PE%' AND name LIKE '%白底%' ORDER BY name")
products = cursor.fetchall()
for product in products:
    print(f"ID: {product[0]}, 型号: {product[1]}, 名称: {product[2]}, 价格: {product[3]}")

print("\n=== 查找9803型号产品 ===")
cursor.execute("SELECT * FROM products WHERE model_number LIKE '%9803%'")
products_9803 = cursor.fetchall()
for product in products_9803:
    print(f"ID: {product[0]}, 型号: {product[1]}, 名称: {product[2]}, 价格: {product[3]}")

conn.close()
