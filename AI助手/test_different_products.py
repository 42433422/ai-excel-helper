#!/usr/bin/env python3
# 测试不同产品的编号模式匹配

from ai_augmented_parser import AIAugmentedShipmentParser

def test_different_products():
    """测试不同产品的编号模式匹配"""
    print("=== 测试不同产品的编号模式匹配 ===")
    
    # 测试不同产品的名称+编号组合
    test_cases = [
        # PE封固底漆相关
        "蕊芯一桶PE封固底漆，6824A规格25",
        "蕊芯一桶6824A，PE封固底漆规格25",
        "蕊芯一桶，6824A规格25",
        "蕊芯一桶，PE封固底漆规格25",
        
        # PE稀释剂相关
        "蕊芯一桶PE稀释剂，9806A规格25",
        "蕊芯一桶9806A，PE稀释剂规格25",
        "蕊芯一桶，9806A规格25",
        "蕊芯一桶，PE稀释剂规格25",
        
        # PU哑光银珠漆相关
        "蕊芯一桶PU哑光银珠漆，24-4-8规格25",
        "蕊芯一桶24-4-8，PU哑光银珠漆规格25",
        "蕊芯一桶，24-4-8规格25",
        "蕊芯一桶，PU哑光银珠漆规格25",
    ]
    
    parser = AIAugmentedShipmentParser()
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: '{test_text}'")
        print("-" * 60)
        
        # 测试AI提取结果
        ai_result = parser._call_deepseek_for_product_extraction(test_text, number_mode=True)
        
        if ai_result and ai_result.get("products"):
            print(f"AI提取结果:")
            print(f"  购买单位: {ai_result.get('purchase_unit', 'N/A')}")
            
            for j, product in enumerate(ai_result.get('products', []), 1):
                print(f"  产品 {j}:")
                print(f"    名称: {product.get('name', 'N/A')}")
                print(f"    型号: {product.get('model_number', 'N/A')}")
        
        # 测试最终解析结果
        final_result = parser.parse(test_text, custom_mode=False, number_mode=True)
        
        if final_result.products:
            print(f"最终解析结果:")
            for j, product in enumerate(final_result.products, 1):
                print(f"  产品 {j}: {product['name']} ({product['model_number']}) - {product['quantity_tins']}桶")
        else:
            print(f"解析失败")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_different_products()