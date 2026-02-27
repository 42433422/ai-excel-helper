#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试AI原始提取结果
"""

from ai_augmented_parser import AIAugmentedShipmentParser

def test_ai_extraction():
    """测试AI原始提取结果"""
    
    parser = AIAugmentedShipmentParser()
    
    # 测试订单
    test_order = "七彩乐园10桶9803A规格25，PE稀释剂180kg1桶，PE哑光白面漆5桶规格28"
    
    print(f"=== 测试AI原始提取结果 ===")
    print(f"订单文本: {test_order}")
    print()
    
    # 调用AI提取方法
    ai_result = parser._call_deepseek_for_product_extraction(test_order, True)
    
    if ai_result and ai_result.get("products"):
        print("AI提取的原始结果:")
        for i, product in enumerate(ai_result["products"]):
            print(f"\n产品 {i+1}:")
            print(f"  名称: {product.get('name', 'N/A')}")
            print(f"  型号: {product.get('model_number', 'N/A')}")
            print(f"  数量(KG): {product.get('quantity_kg', 'N/A')}")
            print(f"  数量(桶): {product.get('quantity_tins', 'N/A')}")
            print(f"  规格: {product.get('tin_spec', 'N/A')}")
            print(f"  原始数据: {product}")
    else:
        print("AI提取失败")

if __name__ == "__main__":
    test_ai_extraction()