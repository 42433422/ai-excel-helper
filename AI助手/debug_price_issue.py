#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试价格获取问题
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_price_issue():
    """调试价格获取问题"""
    
    print("=" * 80)
    print("🔍 调试价格获取问题")
    print("=" * 80)
    
    from ai_augmented_parser import AIAugmentedShipmentParser
    ai_parser = AIAugmentedShipmentParser()
    
    # 测试数据库匹配
    test_cases = [
        ("PE白底漆", "蕊芯家私1"),
        ("9806", "蕊芯家私1"),
        ("PE稀释剂", "蕊芯家私1"),
        ("9806A", "蕊芯家私1")
    ]
    
    print("🔍 测试数据库匹配:")
    for text, unit_name in test_cases:
        print(f"\n测试: '{text}' 单位: '{unit_name}'")
        
        try:
            db_product = ai_parser._match_product_from_db(text, unit_name, number_mode=False)
            print(f"  返回结果: {db_product}")
            
            if db_product:
                price = db_product.get("price", 0.0)
                print(f"  价格: ¥{price}")
            else:
                print(f"  ❌ 未匹配到产品")
                
        except Exception as e:
            print(f"  ❌ 匹配失败: {e}")
    
    # 测试完整解析
    print(f"\n🔍 测试完整解析:")
    test_order = "蕊芯1Pe白底漆10桶，规格28KGPE稀释剂:1桶，规格180KG"
    
    try:
        result = ai_parser.parse(test_order)
        
        print(f"完整解析结果:")
        print(f"  客户: {result.purchase_unit}")
        print(f"  产品数量: {len(result.products)}")
        
        for i, product in enumerate(result.products, 1):
            print(f"  产品 {i}:")
            print(f"    名称: {product['name']}")
            print(f"    型号: {product['model_number']}")
            print(f"    单价: ¥{product['unit_price']}")
            print(f"    数量: {product['quantity_kg']}kg")
            print(f"    金额: ¥{product['amount']}")
            
            # 计算期望金额
            expected_amount = product['quantity_kg'] * product['unit_price']
            print(f"    期望金额: ¥{expected_amount}")
            
    except Exception as e:
        print(f"完整解析失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_price_issue()