#!/usr/bin/env python3
import sqlite3
import os
import shutil

# 清理缓存
cache_dir = '__pycache__'
if os.path.exists(cache_dir):
    shutil.rmtree(cache_dir)

# 重新导入并测试
from ai_augmented_parser import AIAugmentedShipmentParser
parser = AIAugmentedShipmentParser()

# 测试完整解析
test_text = '七彩乐园PE白底10桶'
print(f"=== 测试完整解析: {test_text} ===")
result = parser.parse(test_text)
print(f"购买单位: {result.purchase_unit}")
for i, product in enumerate(result.products, 1):
    print(f"产品 {i}: {product.get('model_number', '')} - {product.get('name', '')}")

print("\n=== 检查单位数据库映射 ===")
print(f"七彩乐园 -> unit_databases/七彩乐园.db: {os.path.exists('unit_databases/七彩乐园.db')}")

print("\n=== 检查七彩乐园数据库内容 ===")
conn = sqlite3.connect('unit_databases/七彩乐园.db')
cursor = conn.cursor()
cursor.execute("SELECT model_number, name, price FROM products WHERE name LIKE '%PE%' AND name LIKE '%白底%' ORDER BY model_number")
products = cursor.fetchall()
for product in products:
    print(f"  {product[0]} - {product[1]} (价格: {product[2]})")

conn.close()
