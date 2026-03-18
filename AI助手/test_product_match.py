import sys
sys.path.insert(0, '.')
from ai_augmented_parser import AIAugmentedShipmentParser

# 创建解析器
parser = AIAugmentedShipmentParser()

# 测试七彩乐园的产品匹配
test_cases = [
    "PE白底漆",
    "哑光银珠",
    "PE白底稀释剂",
]

print("=== 测试产品匹配 ===\n")

for product_name in test_cases:
    print(f"搜索: {product_name}")
    result = parser._match_product_from_db(product_name, "七彩乐园", False)
    if result:
        print(f"  匹配到: {result['name']} (型号: {result['model_number']})")
    else:
        print(f"  未匹配到产品")
    print()
