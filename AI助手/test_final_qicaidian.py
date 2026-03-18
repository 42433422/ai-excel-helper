#!/usr/bin/env python3
import os

# 清理缓存文件
cache_dir = '__pycache__'
if os.path.exists(cache_dir):
    for file in os.listdir(cache_dir):
        if file.startswith('ai_augmented_parser') and file.endswith('.pyc'):
            os.remove(os.path.join(cache_dir, file))

from ai_augmented_parser import AIAugmentedShipmentParser

parser = AIAugmentedShipmentParser()
text = '七彩乐园PE白底10桶，PE稀释剂180kg1桶，PE哑光白面漆5桶'
result = parser.parse(text)

print('=== AI解析结果 ===')
print(f'购买单位: {result.purchase_unit}')
print(f'产品数量: {len(result.products)}')
print()
for i, product in enumerate(result.products, 1):
    print(f'产品 {i}:')
    print(f'  名称: {product.get("name", "")}')
    print(f'  型号: {product.get("model_number", "")}')
    print(f'  数量_kg: {product.get("quantity_kg", 0)}')
    print(f'  数量_桶: {product.get("quantity_tins", 0)}')
    print()
