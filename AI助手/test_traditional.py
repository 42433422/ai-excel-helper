import sys
sys.path.insert(0, '.')
from ai_augmented_parser import AIAugmentedShipmentParser

parser = AIAugmentedShipmentParser()

# 测试传统解析器提取的产品
test_input = "七彩乐园Pe白底漆10桶规格28, 哑光银珠1桶规格20Kg，PE白底漆稀料1桶规格180"
print(f"输入: {test_input}\n")

# 传统解析器提取的产品
traditional_unit = parser._extract_purchase_unit(test_input)
print(f"购买单位: {traditional_unit}")

traditional_products = parser._split_products(test_input, traditional_unit)
print(f"传统解析器提取的产品: {traditional_products}")

# 测试每个产品的匹配
print("\n=== 测试每个产品的匹配 ===\n")
for p in traditional_products:
    result = parser._match_product_from_db(p, "七彩乐园", False)
    if result:
        print(f"'{p}' -> {result['name']} (型号: {result['model_number']})")
    else:
        print(f"'{p}' -> 未匹配")
