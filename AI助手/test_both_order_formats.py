#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试两种订单格式的客户匹配
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_both_order_formats():
    """测试两种订单格式的客户匹配"""
    
    # 创建解析器实例
    from shipment_parser import ShipmentParser
    parser = ShipmentParser(db_path="products.db")
    
    # 测试两种订单格式
    test_orders = [
        "蕊芯Pe白底漆10桶，规格28KGPE稀释剂:1桶，规格180KG",
        "蕊芯1Pe白底漆10桶，规格28KGPE稀释剂:1桶，规格180KG"
    ]
    
    print("=" * 60)
    print("🎯 测试两种订单格式的客户匹配")
    print("=" * 60)
    
    for i, order_text in enumerate(test_orders, 1):
        print(f"\n🧪 测试订单 {i}:")
        print(f"订单: {order_text}")
        
        # 解析订单
        try:
            result = parser.parse(order_text)
            
            print(f"\n✅ 解析结果:")
            print(f"  客户单位: {result.purchase_unit}")
            print(f"  产品数量: {len(result.products)}个")
            print(f"  总重量: {result.quantity_kg}kg")
            print(f"  总桶数: {result.quantity_tins}桶")
            
            # 检查客户匹配结果
            print(f"\n🔍 客户匹配分析:")
            if "蕊芯家私" in result.purchase_unit:
                print(f"  ✅ 客户匹配成功: {result.purchase_unit}")
                if i == 1:
                    print(f"     - '蕊芯' → '蕊芯家私' ✅")
                else:
                    print(f"     - '蕊芯1' → '蕊芯家私1' ✅")
            elif "蕊芯" in result.purchase_unit:
                print(f"  ⚠️  客户匹配部分成功: {result.purchase_unit}")
                print(f"     - 应该匹配到'蕊芯家私'但匹配到了'{result.purchase_unit}'")
            else:
                print(f"  ❌ 客户匹配失败")
            
            # 显示产品详情
            print(f"\n📦 产品详情:")
            for j, product in enumerate(result.products, 1):
                print(f"  产品 {j}: {product['name']} - {product['quantity_tins']}桶 × {product['tin_spec']}kg = {product['quantity_kg']}kg")
                
        except Exception as e:
            print(f"  ❌ 解析失败: {e}")
        
        print("-" * 50)
    
    # 总结测试结果
    print(f"\n🎯 总结:")
    print(f"测试了两种订单格式:")
    print(f"1. '蕊芯' 开头 → 应该匹配到 '蕊芯家私'")
    print(f"2. '蕊芯1' 开头 → 应该匹配到 '蕊芯家私1'")
    print(f"\n请检查上述结果是否都匹配正确！")

if __name__ == "__main__":
    test_both_order_formats()