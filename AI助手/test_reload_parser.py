#!/usr/bin/env python3
import os
import shutil

# 清理缓存文件
cache_dir = '__pycache__'
if os.path.exists(cache_dir):
    shutil.rmtree(cache_dir)

# 强制重新加载
import importlib
import sys
sys.path.insert(0, os.getcwd())

# 重新导入
from ai_augmented_parser import AIAugmentedShipmentParser
parser = AIAugmentedShipmentParser()
result = parser.parse('七彩乐园PE白底10桶')
print('=== 测试重新加载的解析器 ===')
print(f'购买单位: {result.purchase_unit}')
for i, product in enumerate(result.products, 1):
    print(f'产品 {i}: {product.get("model_number", "")} - {product.get("name", "")}')
