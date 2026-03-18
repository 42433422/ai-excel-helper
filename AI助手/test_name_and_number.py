#!/usr/bin/env python3
# 测试编号模式下的名称+编号同时识别

from ai_augmented_parser import AIAugmentedShipmentParser

def test_name_and_number():
    """测试编号模式下的名称+编号同时识别"""
    print("=== 测试编号模式下的名称+编号同时识别 ===")
    
    # 测试不同的输入格式
    test_cases = [
        "蕊芯一桶哑光银珠漆，24-4-8规格25",  # 名称+编号
        "蕊芯一桶24-4-8，哑光银珠漆规格25",  # 编号+名称
        "蕊芯哑光银珠漆24-4-8一桶规格25",    # 名称编号混合
        "蕊芯一桶，24-4-8规格25",           # 只有编号
        "蕊芯一桶，哑光银珠漆规格25"         # 只有名称
    ]
    
    parser = AIAugmentedShipmentParser()
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: '{test_text}'")
        print("-" * 50)
        
        # 测试AI提取结果
        ai_result = parser._call_deepseek_for_product_extraction(test_text, number_mode=True)
        
        if ai_result and ai_result.get("products"):
            print(f"AI提取结果:")
            print(f"  购买单位: {ai_result.get('purchase_unit', 'N/A')}")
            
            for j, product in enumerate(ai_result.get('products', []), 1):
                print(f"  产品 {j}:")
                print(f"    名称: {product.get('name', 'N/A')}")
                print(f"    型号: {product.get('model_number', 'N/A')}")
                print(f"    数量: {product.get('quantity_tins', 0)}桶, {product.get('quantity_kg', 0)}公斤")
        
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
    test_name_and_number()