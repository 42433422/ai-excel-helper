#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试AI增强解析器的产品编号识别
"""

import sys
import os

# 添加AI助手目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'AI助手'))

from ai_augmented_parser import AIAugmentedShipmentParser

def test_ai_parser():
    """测试AI增强解析器"""
    parser = AIAugmentedShipmentParser()
    
    # 测试订单文本
    test_cases = [
        "七彩乐园一桶9803规格28",
        "蕊芯10桶9806规格28，1桶9806a规格280",
        "蕊芯Pe白底漆10桶，规格28KG,哑光银珠:1桶，规格20Kg，PE稀释剂:1桶，规格180KG"
    ]
    
    for i, order_text in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}:")
        print(f"订单文本: {order_text}")
        print("=" * 80)
        
        # 测试编号模式
        print("\n测试编号模式:")
        parsed_order_number_mode = parser.parse(order_text, number_mode=True)
        
        print(f"购买单位: {parsed_order_number_mode.purchase_unit}")
        print(f"产品数量: {len(parsed_order_number_mode.products)}")
        print(f"有效: {parsed_order_number_mode.is_valid()}")
        
        for j, product in enumerate(parsed_order_number_mode.products, 1):
            print(f"\n产品 {j}:")
            print(f"  型号: {product.get('model_number', '未知')}")
            print(f"  名称: {product.get('name', '未知')}")
            print(f"  数量(kg): {product.get('quantity_kg', 0)}")
            print(f"  数量(桶): {product.get('quantity_tins', 0)}")
            print(f"  规格: {product.get('tin_spec', 0)}")
            print(f"  单价: {product.get('unit_price', 0)}")
            print(f"  金额: {product.get('amount', 0)}")
        
        # 测试名称模式
        print("\n" + "=" * 80)
        print("测试名称模式:")
        parsed_order_name_mode = parser.parse(order_text, number_mode=False)
        
        print(f"购买单位: {parsed_order_name_mode.purchase_unit}")
        print(f"产品数量: {len(parsed_order_name_mode.products)}")
        print(f"有效: {parsed_order_name_mode.is_valid()}")
        
        for j, product in enumerate(parsed_order_name_mode.products, 1):
            print(f"\n产品 {j}:")
            print(f"  型号: {product.get('model_number', '未知')}")
            print(f"  名称: {product.get('name', '未知')}")
            print(f"  数量(kg): {product.get('quantity_kg', 0)}")
            print(f"  数量(桶): {product.get('quantity_tins', 0)}")
            print(f"  规格: {product.get('tin_spec', 0)}")
            print(f"  单价: {product.get('unit_price', 0)}")
            print(f"  金额: {product.get('amount', 0)}")
        
        print("\n" + "=" * 80)

if __name__ == "__main__":
    test_ai_parser()
