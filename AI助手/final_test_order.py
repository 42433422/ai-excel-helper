#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终订单测试
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def final_test_order():
    """最终测试订单"""
    
    # 创建解析器实例
    from shipment_parser import ShipmentParser
    parser = ShipmentParser(db_path="products.db")
    
    # 测试您的原始订单
    order_text = "蕊芯1Pe白底漆10桶，规格28KG,24-4-8 哑光银珠:1桶，规格20Kg，PE稀释剂:1桶，规格180KG"
    
    print("=== 最终订单解析测试 ===")
    print(f"订单: {order_text}")
    print()
    
    # 解析订单
    result = parser.parse(order_text)
    
    print(f"✅ 客户单位: {result.purchase_unit}")
    print(f"✅ 产品数量: {len(result.products)}个")
    print()
    
    # 根据数据库中的实际产品信息，手动验证匹配
    expected_products = [
        {
            "name": "PE白底漆",
            "model": "9806", 
            "price": 10.1,
            "spec": 28.0
        },
        {
            "name": "PU哑光浅灰银珠漆",
            "model": "24-4-8*", 
            "price": 24.0,
            "spec": 20.0
        },
        {
            "name": "PE白底漆稀释剂",
            "model": "9806A", 
            "price": 7.0,
            "spec": 180.0
        }
    ]
    
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
        
        # 检查是否匹配到预期产品
        if i <= len(expected_products):
            expected = expected_products[i-1]
            if expected["name"] in product['name'] or product['name'] in expected["name"]:
                print(f"  ✅ 匹配到预期产品: {expected['name']}")
            else:
                print(f"  ⚠️  未匹配到预期产品: {expected['name']}")
        print()
    
    print(f"📋 汇总:")
    print(f"  总重量: {result.quantity_kg}kg")
    print(f"  总桶数: {result.quantity_tins}桶")
    print(f"  总金额: ¥{result.amount}")
    
    # 测试新的订单格式
    print(f"\n" + "="*50)
    print(f"=== 测试新订单格式 ===")
    
    new_order_text = "蕊芯1Pe白底漆10桶，规格28,24-4-8 哑光银珠:1桶规格20PE稀释剂:1桶规格180"
    print(f"订单: {new_order_text}")
    print()
    
    result2 = parser.parse(new_order_text)
    
    print(f"✅ 客户单位: {result2.purchase_unit}")
    print(f"✅ 产品数量: {len(result2.products)}个")
    print()
    
    for i, product in enumerate(result2.products, 1):
        print(f"产品 {i}:")
        print(f"  名称: {product['name']}")
        print(f"  数量: {product['quantity_tins']}桶")
        print(f"  规格: {product['tin_spec']}kg/桶")
        print(f"  总重量: {product['quantity_kg']}kg")
        print()
    
    print(f"📋 汇总:")
    print(f"  总重量: {result2.quantity_kg}kg")
    print(f"  总桶数: {result2.quantity_tins}桶")

if __name__ == "__main__":
    final_test_order()