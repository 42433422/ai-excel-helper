import sys
sys.path.insert(0, '.')
from ai_augmented_parser import AIAugmentedShipmentParser

parser = AIAugmentedShipmentParser()

# 测试用户实际输入
test_input = "七彩乐园Pe白底漆10桶规格28, 哑光银珠1桶规格20Kg，PE白底漆稀料1桶规格180"
print(f"输入: {test_input}\n")

# 传统解析器提取的产品
traditional_unit = parser._extract_purchase_unit(test_input)
print(f"传统解析器购买单位: {traditional_unit}")

traditional_products = parser._split_products(test_input, traditional_unit)
print(f"传统解析器产品: {traditional_products}")

# AI 解析结果
ai_result = parser._call_deepseek_for_product_extraction(test_input, False)
print(f"\nAI购买单位: {ai_result.get('purchase_unit', '')}")
print(f"AI产品列表:")
for i, p in enumerate(ai_result.get('products', []), 1):
    print(f"  {i}. {p.get('name')} (型号: {p.get('model_number')})")

# 测试匹配
print("\n=== 测试产品匹配 ===\n")
for i, ai_product in enumerate(ai_result.get('products', []), 1):
    product_name = ai_product.get("name", "")
    print(f"AI产品 {i}: '{product_name}'")
    
    # 首先尝试用 AI 产品名称匹配
    db_product = parser._match_product_from_db(product_name, traditional_unit, False)
    if db_product:
        print(f"  AI名称匹配成功: {db_product['name']} (型号: {db_product['model_number']})")
    else:
        print(f"  AI名称匹配失败")
        
        # 尝试用传统解析的产品匹配
        for trad_product in traditional_products:
            if product_name in trad_product:
                db_product2 = parser._match_product_from_db(trad_product, traditional_unit, False)
                if db_product2:
                    print(f"  传统解析匹配成功: {db_product2['name']} (型号: {db_product2['model_number']})")
                    break
    print()
