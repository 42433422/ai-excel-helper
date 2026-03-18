#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新的订单格式
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_new_order_pattern():
    """测试新的订单格式"""
    
    # 创建解析器实例
    from shipment_parser import ShipmentParser
    parser = ShipmentParser(db_path="products.db")
    
    # 测试您的订单格式
    order_text = "蕊芯Pe白底漆10桶，规格28KGPE稀释剂:1桶，规格180KG"
    
    print("=== 测试新订单格式 ===")
    print(f"订单: {order_text}")
    print()
    
    # 解析订单
    result = parser.parse(order_text)
    
    print(f"✅ 客户单位: {result.purchase_unit}")
    print(f"✅ 产品数量: {len(result.products)}个")
    print()
    
    for i, product in enumerate(result.products, 1):
        print(f"产品 {i}:")
        print(f"  名称: {product['name']}")
        print(f"  型号: {product['model_number']}")
        print(f"  数量: {product['quantity_tins']}桶")
        print(f"  规格: {product['tin_spec']}kg/桶")
        print(f"  总重量: {product['quantity_kg']}kg")
        print(f"  单价: ¥{product['unit_price']}")
        print(f"  金额: ¥{product['amount']}")
        print()
    
    print(f"📋 汇总:")
    print(f"  总重量: {result.quantity_kg}kg")
    print(f"  总桶数: {result.quantity_tins}桶")
    print(f"  总金额: ¥{result.amount}")
    
    # 分析结果
    if result.purchase_unit and "蕊芯" in result.purchase_unit:
        print(f"\n✅ 客户匹配成功: {result.purchase_unit}")
    else:
        print(f"\n❌ 客户匹配失败")
    
    if len(result.products) > 0:
        print(f"✅ 产品分割成功: {len(result.products)}个产品")
    else:
        print(f"❌ 产品分割失败")
    
    # 测试分割逻辑
    print(f"\n=== 分析产品分割 ===")
    print("原始文本:", order_text)
    print("移除客户后:", order_text.replace("蕊芯", "").strip())
    
    # 测试客户匹配
    print(f"\n=== 客户匹配测试 ===")
    test_customer_matching(parser, "蕊芯Pe白底漆10桶")
    
def test_customer_matching(parser, text):
    """测试客户匹配逻辑"""
    customer = parser._extract_purchase_unit(text)
    print(f"输入: {text}")
    print(f"匹配结果: {customer}")
    
    if customer and "蕊芯" in customer:
        print("✅ 客户匹配成功")
    else:
        print("❌ 客户匹配失败")

if __name__ == "__main__":
    test_new_order_pattern()