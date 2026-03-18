#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试DocumentAPIGenerator价格丢失问题
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_api_price_loss():
    """调试DocumentAPIGenerator价格丢失问题"""
    
    print("=" * 80)
    print("🔍 调试DocumentAPIGenerator价格丢失问题")
    print("=" * 80)
    
    from shipment_document import DocumentAPIGenerator
    
    doc_generator = DocumentAPIGenerator()
    
    test_order = "蕊芯1Pe白底漆10桶，规格28KGPE稀释剂:1桶，规格180KG"
    
    print(f"测试订单: {test_order}")
    
    try:
        # 测试DocumentAPIGenerator内部逻辑
        print(f"\n🔍 1. 测试AI解析器调用:")
        
        # 直接调用内部解析器
        from ai_augmented_parser import AIAugmentedShipmentParser
        ai_parser = AIAugmentedShipmentParser(doc_generator.generator.db_path)
        
        parsed_order = ai_parser.parse(test_order, custom_mode=False, number_mode=False)
        
        print(f"  AI解析器结果:")
        print(f"    购买单位: {parsed_order.purchase_unit}")
        print(f"    产品数量: {len(parsed_order.products)}")
        
        for i, product in enumerate(parsed_order.products, 1):
            print(f"    产品{i}: {product['name']} - {product['model_number']} - ¥{product['unit_price']}")
        
        # 检查parsed_order.is_valid()
        print(f"\n🔍 2. 检查is_valid():")
        is_valid = parsed_order.is_valid()
        print(f"  is_valid(): {is_valid}")
        
        # 检查to_dict()
        print(f"\n🔍 3. 检查to_dict():")
        parsed_dict = parsed_order.to_dict()
        print(f"  products字段存在: {'products' in parsed_dict}")
        if 'products' in parsed_dict:
            print(f"  products数量: {len(parsed_dict['products'])}")
            for i, product in enumerate(parsed_dict['products'], 1):
                print(f"    产品{i}: {product.get('name', '无')} - ¥{product.get('unit_price', 0)}")
        
        # 检查get_purchase_unit_info
        print(f"\n🔍 4. 检查购买单位信息:")
        if parsed_order.purchase_unit:
            purchase_unit = doc_generator.generator._get_purchase_unit_info(parsed_order.purchase_unit)
            print(f"  购买单位: {purchase_unit}")
        
        # 测试完整的parse_and_generate
        print(f"\n🔍 5. 测试完整的parse_and_generate:")
        result = doc_generator.parse_and_generate(
            order_text=test_order,
            custom_mode=False,
            number_mode=False,
            generate_labels=False
        )
        
        print(f"  完整结果成功: {result.get('success', False)}")
        
        if result.get('success'):
            parsed_data = result.get('parsed_data', {})
            print(f"  解析数据存在: {'products' in parsed_data}")
            if 'products' in parsed_data:
                print(f"  products数量: {len(parsed_data['products'])}")
                for i, product in enumerate(parsed_data['products'], 1):
                    print(f"    产品{i}: {product.get('name', '无')} - ¥{product.get('unit_price', 0)}")
        else:
            print(f"  错误信息: {result.get('message', '未知')}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_api_price_loss()