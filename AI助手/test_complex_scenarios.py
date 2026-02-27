#!/usr/bin/env python3
# 测试复杂场景下的编号模式智能匹配

from ai_augmented_parser import AIAugmentedShipmentParser

def test_complex_scenarios():
    """测试复杂场景下的编号模式智能匹配"""
    print("=== 测试复杂场景下的编号模式智能匹配 ===")
    
    # 测试可能产生歧义的场景
    test_cases = [
        # 多个产品的情况
        "蕊芯一桶6824A，一桶PE稀释剂9806A，一桶24-4-8规格25",
        
        # 不一致的信息（名称和编号不匹配的情况）
        "蕊芯一桶PE封固底漆，24-4-8规格25",  # 名称是PE封固底漆，但编号是24-4-8
        
        # 部分匹配的情况
        "蕊芯一桶PE封固漆，6824A规格25",  # 名称略有不准确
        
        # 编号模式vs非编号模式的对比
        "蕊芯一桶PE封固底漆，6824A规格25",
        
        # 错误编号的情况
        "蕊芯一桶PE封固底漆，9999A规格25",  # 不存在的编号
    ]
    
    parser = AIAugmentedShipmentParser()
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: '{test_text}'")
        print("-" * 70)
        
        # 测试编号模式
        print("编号模式:")
        ai_result = parser._call_deepseek_for_product_extraction(test_text, number_mode=True)
        
        if ai_result and ai_result.get("products"):
            print(f"  AI提取结果:")
            for j, product in enumerate(ai_result.get('products', []), 1):
                print(f"    产品 {j}: {product.get('name', 'N/A')} ({product.get('model_number', 'N/A')})")
        
        final_result = parser.parse(test_text, custom_mode=False, number_mode=True)
        if final_result.products:
            print(f"  最终匹配结果:")
            for j, product in enumerate(final_result.products, 1):
                print(f"    产品 {j}: {product['name']} ({product['model_number']}) - {product['quantity_tins']}桶")
        else:
            print(f"  匹配失败")
        
        # 测试非编号模式进行对比
        print("非编号模式(对比):")
        normal_result = parser.parse(test_text, custom_mode=False, number_mode=False)
        if normal_result.products:
            print(f"  最终匹配结果:")
            for j, product in enumerate(normal_result.products, 1):
                print(f"    产品 {j}: {product['name']} ({product['model_number']}) - {product['quantity_tins']}桶")
        else:
            print(f"  匹配失败")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_complex_scenarios()