#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试前端API是否使用AI解析器
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_api_with_ai():
    """测试前端API是否使用AI解析器"""
    
    print("=" * 80)
    print("🧪 测试前端API是否使用AI解析器")
    print("=" * 80)
    
    from shipment_document import DocumentAPIGenerator
    
    # 创建文档生成器（前端使用的）
    doc_generator = DocumentAPIGenerator()
    
    print(f"文档生成器类型: {type(doc_generator).__name__}")
    
    # 测试订单
    test_order = "蕊芯1Pe白底漆10桶，规格28KGPE稀释剂:1桶，规格180KG"
    
    print(f"\n🧪 测试订单: {test_order}")
    
    try:
        # 模拟前端调用
        result = doc_generator.parse_and_generate(
            order_text=test_order,
            custom_mode=False,  # 模拟前端不勾选自定义模式
            number_mode=False,
            generate_labels=False
        )
        
        print(f"\n✅ 解析结果:")
        if result.get('success'):
            print(f"  成功: {result['success']}")
            
            parsed_data = result.get('parsed_data', {})
            if parsed_data:
                print(f"  购买单位: {parsed_data.get('purchase_unit', '未识别')}")
                print(f"  产品数量: {len(parsed_data.get('products', []))}")
                print(f"  总重量: {parsed_data.get('quantity_kg', 0)}kg")
                print(f"  总金额: ¥{parsed_data.get('amount', 0)}")
                
                # 检查是否使用了AI解析方法
                parse_method = parsed_data.get('parse_method', '')
                if parse_method == 'ai':
                    print(f"  ✅ 使用AI解析方法")
                else:
                    print(f"  ⚠️  使用{parse_method}解析方法")
                
                print(f"\n📦 产品详情:")
                for i, product in enumerate(parsed_data.get('products', []), 1):
                    print(f"  产品 {i}: {product.get('name', '未知')} - {product.get('model_number', '无')} - ¥{product.get('unit_price', 0)}")
        else:
            print(f"  ❌ 失败: {result.get('message', '未知错误')}")
            
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🎯 验证AI解析器特性")
    print("=" * 60)
    
    # 验证AI解析器特定功能
    try:
        from ai_augmented_parser import AIAugmentedShipmentParser
        
        ai_parser = AIAugmentedShipmentParser()
        
        print(f"AI解析器类型: {type(ai_parser).__name__}")
        
        # 测试AI解析器特有功能
        ai_result = ai_parser.parse(test_order, custom_mode=False, number_mode=False)
        
        print(f"AI解析结果:")
        print(f"  购买单位: {ai_result.purchase_unit}")
        print(f"  解析方法: {ai_result.parsed_data.get('parse_method', '') if hasattr(ai_result, 'parsed_data') else '未知'}")
        
        if hasattr(ai_result, 'parsed_data') and ai_result.parsed_data:
            parse_method = ai_result.parsed_data.get('parse_method', '')
            if parse_method == 'ai':
                print(f"  ✅ AI解析器正常工作")
            else:
                print(f"  ⚠️  AI解析器未使用AI方法")
        
    except Exception as e:
        print(f"❌ AI解析器测试失败: {e}")

if __name__ == "__main__":
    test_api_with_ai()