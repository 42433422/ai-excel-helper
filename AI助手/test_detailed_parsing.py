#!/usr/bin/env python3
import os
import sys

# 设置调试输出
sys.stdout = sys.stderr

from ai_augmented_parser import AIAugmentedShipmentParser

print("=== 开始详细测试 ===")
parser = AIAugmentedShipmentParser()

# 测试更详细的解析过程
test_text = '七彩乐园PE白底10桶'
print(f"测试文本: {test_text}")

# 直接调用AI匹配逻辑
try:
    print("\n=== 直接测试AI产品匹配 ===")
    # 这里应该会有一些调试信息
    result = parser.parse(test_text)
    print(f"\n最终结果:")
    print(f"购买单位: {result.purchase_unit}")
    for i, product in enumerate(result.products, 1):
        print(f"产品 {i}: {product.get('model_number', '')} - {product.get('name', '')}")
except Exception as e:
    print(f"出错: {e}")
    import traceback
    traceback.print_exc()
