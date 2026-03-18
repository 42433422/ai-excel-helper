#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终验证测试 - 验证AI解析器改进效果
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def final_validation_test():
    """最终验证测试"""
    
    print("=" * 80)
    print("🎯 最终验证测试 - AI解析器改进效果")
    print("=" * 80)
    
    # 测试1: 直接调用AI解析器
    print("\n🔍 测试1: 直接调用AI解析器")
    print("-" * 50)
    
    from ai_augmented_parser import AIAugmentedShipmentParser
    ai_parser = AIAugmentedShipmentParser()
    
    test_order = "蕊芯1Pe白底漆10桶，规格28KGPE稀释剂:1桶，规格180KG"
    print(f"测试订单: {test_order}")
    
    try:
        result = ai_parser.parse(test_order)
        print(f"✅ 解析成功:")
        print(f"  客户: {result.purchase_unit}")
        print(f"  产品数量: {len(result.products)}个")
        print(f"  总重量: {result.quantity_kg}kg")
        
        # 检查是否使用了AI解析
        if hasattr(result, 'parsed_data') and result.parsed_data:
            parse_method = result.parsed_data.get('parse_method', '')
            print(f"  解析方法: {parse_method}")
        
        print(f"\n📦 产品详情:")
        for i, product in enumerate(result.products, 1):
            print(f"  产品 {i}: {product['name']} - {product['model_number']} - {product['quantity_tins']}桶 × {product['tin_spec']}kg")
    except Exception as e:
        print(f"❌ 解析失败: {e}")
    
    # 测试2: 验证前端API配置
    print(f"\n🔍 测试2: 验证前端API配置")
    print("-" * 50)
    
    from shipment_api import get_shipment_controller
    controller = get_shipment_controller()
    parser = controller["parser"]
    
    print(f"解析器类型: {type(parser).__name__}")
    
    if "AIAugmentedShipmentParser" in str(type(parser)):
        print("✅ 前端API已配置为使用AI解析器")
    else:
        print("❌ 前端API仍在使用普通解析器")
    
    # 测试3: 验证提示词改进
    print(f"\n🔍 测试3: 验证提示词改进")
    print("-" * 50)
    
    prompt = ai_parser._get_deepseek_product_extraction_prompt()
    if "蕊芯1" in prompt and "9806" in prompt:
        print("✅ 提示词已更新包含特殊规则")
        print("   - 包含客户识别规则")
        print("   - 包含产品型号映射")
    else:
        print("❌ 提示词未更新")
    
    # 总结测试结果
    print(f"\n🎯 总结")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 3
    
    # 检查客户识别
    try:
        result = ai_parser.parse("蕊芯Pe白底漆10桶，规格28KG")
        if "蕊芯家私" in result.purchase_unit:
            print("✅ 测试1: 客户识别正确")
            tests_passed += 1
        else:
            print(f"❌ 测试1: 客户识别错误: {result.purchase_unit}")
    except:
        print("❌ 测试1: 客户识别失败")
    
    # 检查产品型号识别
    try:
        result = ai_parser.parse(test_order)
        has_correct_models = any(p['model_number'] == '9806' for p in result.products)
        if has_correct_models:
            print("✅ 测试2: 产品型号识别正确")
            tests_passed += 1
        else:
            print(f"❌ 测试2: 产品型号识别错误")
    except:
        print("❌ 测试2: 产品型号识别失败")
    
    # 检查AI解析方法
    try:
        if "AIAugmentedShipmentParser" in str(type(parser)):
            print("✅ 测试3: 前端配置AI解析器")
            tests_passed += 1
        else:
            print("❌ 测试3: 前端配置普通解析器")
    except:
        print("❌ 测试3: 前端配置检查失败")
    
    print(f"\n🎉 测试结果: {tests_passed}/{total_tests} 通过")
    
    if tests_passed == total_tests:
        print("🎊 所有测试通过！AI解析器改进成功！")
    elif tests_passed >= 2:
        print("🎯 大部分测试通过，AI解析器基本可用！")
    else:
        print("⚠️  需要进一步改进AI解析器")

if __name__ == "__main__":
    final_validation_test()