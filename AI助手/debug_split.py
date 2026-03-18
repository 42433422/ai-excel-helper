#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试分割逻辑
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_split_logic():
    """调试分割逻辑"""
    try:
        from shipment_parser import ShipmentParser
        
        # 创建解析器实例
        parser = ShipmentParser(db_path="products.db")
        
        # 订单文本
        order_text = "蕊芯1Pe白底漆10桶，规格28,24-4-8 哑光银珠:1桶规格20PE稀释剂:1桶规格180"
        
        print("=== 调试分割逻辑 ===")
        print(f"订单: {order_text}")
        
        # 测试分割方法
        purchase_unit = "蕊芯1"
        products = parser._split_products(order_text, purchase_unit)
        
        print(f"\n分割结果:")
        for i, product in enumerate(products, 1):
            print(f"产品 {i}: {product}")
        
        # 测试数量提取
        print(f"\n=== 数量提取测试 ===")
        for i, product in enumerate(products, 1):
            print(f"\n产品 {i}: {product}")
            quantity_info = parser._extract_quantity(product)
            print(f"  提取的数量: {quantity_info}")
        
    except Exception as e:
        print(f"调试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_split_logic()