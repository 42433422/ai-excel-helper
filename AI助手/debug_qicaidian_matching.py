#!/usr/bin/env python3
import sqlite3
import logging
from ai_augmented_parser import AIAugmentedShipmentParser

# 启用调试日志
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')

# 先检查七彩乐园数据库中的产品
print('=== 检查七彩乐园数据库中的PE相关产品 ===')
conn = sqlite3.connect('unit_databases/七彩乐园.db')
cursor = conn.cursor()
cursor.execute("SELECT model_number, name, price FROM products WHERE name LIKE '%PE%' AND name LIKE '%白底%' ORDER BY model_number")
products = cursor.fetchall()
for product in products:
    print(f'型号: {product[0]}, 名称: {product[1]}, 价格: {product[2]}')
conn.close()

print('\n=== AI解析器测试 ===')
parser = AIAugmentedShipmentParser()

# 测试输入
test_cases = [
    'PE白底10桶',
    'PE白底漆10桶',
    '七彩乐园PE白底10桶'
]

for test_text in test_cases:
    print(f'\n测试输入: "{test_text}"')
    result = parser.parse(test_text)
    print(f'购买单位: {result.purchase_unit}')
    print(f'产品数量: {len(result.products)}')
    for i, product in enumerate(result.products, 1):
        print(f'  产品 {i}: {product.get("model_number", "")} - {product.get("name", "")}')
