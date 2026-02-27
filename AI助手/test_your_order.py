#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试您的原始订单
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shipment_parser import ShipmentParser

def test_your_order():
    # 创建解析器实例
    parser = ShipmentParser(db_path="products.db")
    
    # 您的原始订单
    order_text = "蕊芯1Pe白底漆10桶，规格28KG,24-4-8 哑光银珠:1桶，规格20Kg，PE稀释剂:1桶，规格180KG"
    
    print("=== 您的原始订单解析结果 ===")
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
        print(f"  数量: {product['quantity_tins']}桶")
        print(f"  规格: {product['tin_spec']}kg/桶")
        print(f"  总重量: {product['quantity_kg']}kg")
        print()
    
    print(f"📋 汇总:")
    print(f"  总重量: {result.quantity_kg}kg")
    print(f"  总桶数: {result.quantity_tins}桶")

if __name__ == "__main__":
    test_your_order()