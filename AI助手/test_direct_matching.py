#!/usr/bin/env python3
import os
import shutil

# 清理缓存
cache_dir = '__pycache__'
if os.path.exists(cache_dir):
    shutil.rmtree(cache_dir)

# 重新导入并测试
from ai_augmented_parser import AIAugmentedShipmentParser
parser = AIAugmentedShipmentParser()

# 测试单个产品解析
test_text = 'PE白底10桶'
print(f"=== 测试单个产品: {test_text} ===")
result = parser.parse(test_text)
print(f"购买单位: {result.purchase_unit}")
for i, product in enumerate(result.products, 1):
    print(f"产品 {i}: {product.get('model_number', '')} - {product.get('name', '')}")

print("\n=== 直接测试匹配函数 ===")

# 直接调用匹配函数
conn = sqlite3.connect('unit_databases/七彩乐园.db')
cursor = conn.cursor()
cursor.execute('SELECT * FROM products WHERE name LIKE "%PE%" AND name LIKE "%白底%"')
products = cursor.fetchall()

for product in products:
    print(f"\n测试产品: {product[1]} - {product[2]}")
    
    # 手动调用智能产品匹配函数
    try:
        matched = parser._match_product_from_db("PE白底", products, "unit_db")
        if matched:
            print(f"智能匹配结果: {matched[1]} - {matched[2]}")
        else:
            print("智能匹配: 未匹配")
    except Exception as e:
        print(f"智能匹配出错: {e}")
        
    # 手动调用传统产品匹配函数
    try:
        matched = parser._match_product_from_db("PE白底", products, "traditional")
        if matched:
            print(f"传统匹配结果: {matched[1]} - {matched[2]}")
        else:
            print("传统匹配: 未匹配")
    except Exception as e:
        print(f"传统匹配出错: {e}")

conn.close()
