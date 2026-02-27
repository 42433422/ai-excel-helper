#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试AI解析器价格传递
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_price_passthrough():
    """测试AI解析器价格传递"""
    
    print("=" * 80)
    print("🔍 测试AI解析器价格传递")
    print("=" * 80)
    
    from ai_augmented_parser import AIAugmentedShipmentParser
    
    ai_parser = AIAugmentedShipmentParser()
    
    test_order = "蕊芯1Pe白底漆10桶，规格28KGPE稀释剂:1桶，规格180KG"
    
    print(f"测试订单: {test_order}")
    
    try:
        # 直接使用AI解析器
        result = ai_parser.parse(test_order)
        
        print(f"\n✅ AI解析器直接结果:")
        print(f"  购买单位: {result.purchase_unit}")
        print(f"  产品数量: {len(result.products)}")
        
        for i, product in enumerate(result.products, 1):
            print(f"  产品 {i}:")
            print(f"    名称: {product['name']}")
            print(f"    型号: {product['model_number']}")
            print(f"    单价: ¥{product['unit_price']}")
            print(f"    总重量: {product['quantity_kg']}kg")
            print(f"    金额: ¥{product['amount']}")
        
        # 测试to_dict()方法
        print(f"\n📦 to_dict()方法结果:")
        dict_result = result.to_dict()
        
        if 'products' in dict_result:
            print(f"  products字段存在: {len(dict_result['products'])}个产品")
            
            for i, product in enumerate(dict_result['products'], 1):
                print(f"  产品 {i}:")
                print(f"    名称: {product.get('name', '无')}")
                print(f"    型号: {product.get('model_number', '无')}")
                print(f"    单价: ¥{product.get('unit_price', 0)}")
                print(f"    总重量: {product.get('quantity_kg', 0)}kg")
                print(f"    金额: ¥{product.get('amount', 0)}")
        else:
            print(f"  ❌ products字段不存在")
        
        # 测试parsed_data字段
        if hasattr(result, 'parsed_data') and result.parsed_data:
            print(f"\n📊 parsed_data字段:")
            parse_method = result.parsed_data.get('parse_method', '未知')
            print(f"  解析方法: {parse_method}")
            
            if 'products' in result.parsed_data:
                print(f"  产品数量: {len(result.parsed_data['products'])}")
                
                for i, product in enumerate(result.parsed_data['products'], 1):
                    print(f"  产品 {i}:")
                    print(f"    名称: {product.get('name', '无')}")
                    print(f"    型号: {product.get('model_number', '无')}")
                    print(f"    单价: ¥{product.get('unit_price', 0)}")
                    print(f"    总重量: {product.get('quantity_kg', 0)}kg")
                    print(f"    金额: ¥{product.get('amount', 0)}")
            else:
                print(f"  ❌ parsed_data中没有products字段")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🎯 结论")
    print("=" * 60)
    print("如果AI解析器直接结果有价格，但to_dict()结果价格丢失，")
    print("则说明是序列化过程的问题。")

if __name__ == "__main__":
    test_price_passthrough()