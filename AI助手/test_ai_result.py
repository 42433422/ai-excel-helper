import sys
sys.path.insert(0, '.')
from ai_augmented_parser import AIAugmentedShipmentParser

parser = AIAugmentedShipmentParser()

# 测试 AI 解析
test_input = "七彩乐园Pe白底漆10桶规格28, 哑光银珠1桶规格20Kg，PE白底漆稀料1桶规格180"
print(f"输入: {test_input}\n")

# 直接调用 AI 解析
ai_result = parser._call_deepseek_for_product_extraction(test_input, False)

print("=== AI 解析结果 ===\n")
if ai_result:
    print(f"购买单位: {ai_result.get('purchase_unit', '')}")
    print(f"\n产品列表:")
    for i, p in enumerate(ai_result.get('products', []), 1):
        print(f"  {i}. 名称: {p.get('name')}, 型号: {p.get('model_number')}, 桶数: {p.get('quantity_tins')}")
else:
    print("AI 解析失败")
