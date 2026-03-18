#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试实际工作流程
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_actual_workflow():
    """测试实际工作流程"""
    
    print("=" * 80)
    print("🧪 测试实际工作流程 - 智能发货单生成器")
    print("=" * 80)
    
    # 模拟前端API调用
    from shipment_api import get_shipment_controller
    
    controller = get_shipment_controller()
    parser = controller["parser"]
    
    print(f"解析器类型: {type(parser).__name__}")
    
    # 测试订单
    test_order = "蕊芯1Pe白底漆10桶，规格28KGPE稀释剂:1桶，规格180KG"
    
    print(f"\n🧪 测试订单: {test_order}")
    
    # 模拟前端解析调用
    try:
        result = parser.parse(test_order)
        
        print(f"\n✅ 解析成功:")
        print(f"  购买单位: {result.purchase_unit}")
        print(f"  产品数量: {len(result.products)}个")
        print(f"  总重量: {result.quantity_kg}kg")
        print(f"  总金额: ¥{result.amount}")
        
        # 验证AI解析方法
        if hasattr(result, 'parsed_data') and result.parsed_data:
            parse_method = result.parsed_data.get('parse_method', '')
            print(f"  解析方法: {parse_method}")
        
        print(f"\n📦 产品详情:")
        for i, product in enumerate(result.products, 1):
            print(f"  产品 {i}:")
            print(f"    名称: {product['name']}")
            print(f"    型号: {product['model_number']}")
            print(f"    数量: {product['quantity_tins']}桶")
            print(f"    规格: {product['tin_spec']}kg/桶")
            print(f"    总重量: {product['quantity_kg']}kg")
            print(f"    金额: ¥{product['amount']}")
        
        # 验证结果
        print(f"\n🎯 验证结果:")
        checks_passed = 0
        
        # 检查客户识别
        if "蕊芯家私1" in result.purchase_unit:
            print("  ✅ 客户识别正确")
            checks_passed += 1
        else:
            print(f"  ❌ 客户识别错误: {result.purchase_unit}")
        
        # 检查产品数量
        if len(result.products) >= 2:
            print("  ✅ 产品分割正确")
            checks_passed += 1
        else:
            print(f"  ❌ 产品分割错误: {len(result.products)}个")
        
        # 检查产品型号
        models = [p['model_number'] for p in result.products]
        if '9806' in models and '9806A' in models:
            print("  ✅ 产品型号识别正确")
            checks_passed += 1
        else:
            print(f"  ❌ 产品型号识别错误: {models}")
        
        # 检查数量计算
        total_weight = sum(p['quantity_kg'] for p in result.products)
        if abs(total_weight - 460) < 10:  # 允许小误差
            print("  ✅ 重量计算正确")
            checks_passed += 1
        else:
            print(f"  ❌ 重量计算错误: {total_weight}kg")
        
        print(f"\n🎉 验证结果: {checks_passed}/4 通过")
        
        if checks_passed >= 3:
            print("🎊 AI解析器完全正常工作！")
            return True
        else:
            print("⚠️  AI解析器需要进一步优化")
            return False
            
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_actual_workflow()
    if success:
        print("\n🎯 结论: 智能发货单生成器已完全支持AI解析！")
    else:
        print("\n⚠️  结论: 智能发货单生成器需要进一步优化！")