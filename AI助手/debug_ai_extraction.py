#!/usr/bin/env python3
# 调试AI解析器的产品提取过程

import logging
from ai_augmented_parser import AIAugmentedShipmentParser

def debug_ai_extraction():
    """调试AI解析器的产品提取过程"""
    print("=== 调试AI解析器的产品提取过程 ===")
    
    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # 测试文本
    test_text = "蕊芯一桶，24-4-8规格25"
    print(f"测试文本: '{test_text}'")
    
    # 创建AI解析器实例
    parser = AIAugmentedShipmentParser()
    
    # 1. 直接调用AI提取方法
    print("\n1. 直接调用AI提取方法:")
    ai_result = parser._call_deepseek_for_product_extraction(test_text, number_mode=True)
    
    if ai_result:
        print("AI提取结果:")
        print(f"  购买单位: {ai_result.get('purchase_unit', 'N/A')}")
        print(f"  产品数量: {len(ai_result.get('products', []))}")
        
        for i, product in enumerate(ai_result.get('products', []), 1):
            print(f"  产品 {i}:")
            for key, value in product.items():
                print(f"    {key}: {value}")
            print()
    else:
        print("❌ AI提取失败")
    
    # 2. 查看解析器的内部处理
    print("\n2. 查看解析器的内部处理:")
    
    # 模拟AI解析器的处理过程
    if ai_result and ai_result.get("products"):
        result_purchase_unit = ai_result.get("purchase_unit", "")
        print(f"AI提取的购买单位: '{result_purchase_unit}'")
        
        for i, ai_product in enumerate(ai_result["products"], 1):
            print(f"\n处理AI产品 {i}:")
            print(f"  AI提取的产品名称: '{ai_product.get('name', '')}'")
            print(f"  AI提取的产品型号: '{ai_product.get('model_number', '')}'")
            
            product_name = ai_product.get("name", "")
            model_number = ai_product.get("model_number", "")
            
            print(f"  准备匹配的关键词:")
            print(f"    产品名称: '{product_name}'")
            print(f"    产品型号: '{model_number}'")
            
            # 测试数据库匹配
            if model_number:
                print(f"  测试数据库匹配 (型号): '{model_number}'")
                try:
                    db_product = parser._match_product_from_db(model_number, result_purchase_unit, True)
                    if db_product:
                        print(f"    ✅ 匹配成功: {db_product['name']} ({db_product['model_number']})")
                    else:
                        print(f"    ❌ 匹配失败")
                except Exception as e:
                    print(f"    ❌ 匹配出错: {e}")
            
            if product_name:
                print(f"  测试数据库匹配 (名称): '{product_name}'")
                try:
                    db_product = parser._match_product_from_db(product_name, result_purchase_unit, False)
                    if db_product:
                        print(f"    ✅ 匹配成功: {db_product['name']} ({db_product['model_number']})")
                    else:
                        print(f"    ❌ 匹配失败")
                except Exception as e:
                    print(f"    ❌ 匹配出错: {e}")
    
    # 3. 完整解析流程
    print("\n3. 完整解析流程:")
    final_result = parser.parse(test_text, custom_mode=False, number_mode=True)
    print(f"最终解析结果: {final_result.products}")

if __name__ == "__main__":
    debug_ai_extraction()