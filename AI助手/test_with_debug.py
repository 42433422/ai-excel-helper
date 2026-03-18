#!/usr/bin/env python3
import os
import sys

# 设置调试输出
sys.stdout = sys.stderr

from ai_augmented_parser import AIAugmentedShipmentParser

print("=== 开始测试 ===")
parser = AIAugmentedShipmentParser()
result = parser.parse('七彩乐园PE白底10桶')
print(f"购买单位: {result.purchase_unit}")
for i, product in enumerate(result.products, 1):
    print(f"产品 {i}: {product.get('model_number', '')} - {product.get('name', '')}")
