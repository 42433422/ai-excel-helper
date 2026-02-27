#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试前端是否使用AI解析器
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_frontend_ai_parser():
    """测试前端API是否使用AI解析器"""
    
    from shipment_api import get_shipment_controller
    
    print("=" * 70)
    print("🧪 测试前端API是否使用AI解析器")
    print("=" * 70)
    
    # 获取控制器
    controller = get_shipment_controller()
    parser = controller["parser"]
    
    print(f"解析器类型: {type(parser).__name__}")
    
    # 检查是否是AI解析器
    if "AIAugmentedShipmentParser" in str(type(parser)):
        print("✅ 前端正在使用AI增强解析器")
    else:
        print("❌ 前端仍在使用普通解析器")
        return
    
    # 测试AI解析器功能
    test_order = "蕊芯1Pe白底漆10桶，规格28KGPE稀释剂:1桶，规格180KG"
    
    print(f"\n🧪 测试订单: {test_order}")
    
    try:
        result = parser.parse(test_order)
        
        print(f"\n✅ 解析结果:")
        print(f"  客户单位: {result.purchase_unit}")
        print(f"  产品数量: {len(result.products)}个")
        print(f"  总重量: {result.quantity_kg}kg")
        
        # 检查是否是AI解析结果
        if hasattr(result, 'parsed_data') and result.parsed_data:
            parse_method = result.parsed_data.get('parse_method', '')
            if parse_method == 'ai':
                print(f"  ✅ 使用AI解析方法")
            else:
                print(f"  ⚠️  使用{parse_method}解析方法")
        
        print(f"\n📦 产品详情:")
        for i, product in enumerate(result.products, 1):
            print(f"  产品 {i}: {product['name']} - {product['model_number']} - {product['quantity_tins']}桶")
            
        print(f"\n🎯 验证结果:")
        if "蕊芯家私1" in result.purchase_unit:
            print(f"  ✅ 客户识别正确")
        else:
            print(f"  ❌ 客户识别错误: {result.purchase_unit}")
            
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_frontend_ai_parser()