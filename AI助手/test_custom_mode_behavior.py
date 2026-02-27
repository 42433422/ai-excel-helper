#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试自定义模式行为
确保自定义模式只在明确设置为True时使用
"""

from ai_augmented_parser import AIAugmentedShipmentParser
from shipment_parser import ShipmentParser


def test_custom_mode_behavior():
    """测试自定义模式行为"""
    print("=== 测试自定义模式行为 ===")
    
    # 测试订单
    test_order = "温总编号NC50F，NC哑光清面漆3桶规格25单价14.5"
    
    # 1. 测试AI增强解析器
    print("\n1. 测试AI增强解析器:")
    ai_parser = AIAugmentedShipmentParser()
    
    # 不使用自定义模式（默认）
    result1 = ai_parser.parse(test_order)
    print("   不使用自定义模式:")
    print(f"   购买单位: {result1.purchase_unit}")
    print(f"   产品数量: {len(result1.products)}")
    for i, product in enumerate(result1.products):
        print(f"   产品{i+1}: {product['name']}, 型号: {product['model_number']}, 数量: {product['quantity_tins']}桶, 规格: {product['tin_spec']}kg, 单价: {product['unit_price']}")
    print(f"   解析方法: {result1.parsed_data.get('parse_method', '传统')}")
    
    # 明确使用自定义模式
    result2 = ai_parser.parse(test_order, custom_mode=True)
    print("\n   使用自定义模式:")
    print(f"   购买单位: {result2.purchase_unit}")
    print(f"   产品数量: {len(result2.products)}")
    for i, product in enumerate(result2.products):
        print(f"   产品{i+1}: {product['name']}, 型号: {product['model_number']}, 数量: {product['quantity_tins']}桶, 规格: {product['tin_spec']}kg, 单价: {product['unit_price']}")
    
    # 2. 测试传统解析器
    print("\n2. 测试传统解析器:")
    traditional_parser = ShipmentParser()
    
    # 不使用自定义模式（默认）
    result3 = traditional_parser.parse(test_order)
    print("   不使用自定义模式:")
    print(f"   购买单位: {result3.purchase_unit}")
    print(f"   产品数量: {len(result3.products)}")
    for i, product in enumerate(result3.products):
        print(f"   产品{i+1}: {product['name']}, 型号: {product['model_number']}, 数量: {product['quantity_tins']}桶, 规格: {product['tin_spec']}kg, 单价: {product['unit_price']}")
    
    # 明确使用自定义模式
    result4 = traditional_parser.parse(test_order, custom_mode=True)
    print("\n   使用自定义模式:")
    print(f"   购买单位: {result4.purchase_unit}")
    print(f"   产品数量: {len(result4.products)}")
    for i, product in enumerate(result4.products):
        print(f"   产品{i+1}: {product['name']}, 型号: {product['model_number']}, 数量: {product['quantity_tins']}桶, 规格: {product['tin_spec']}kg, 单价: {product['unit_price']}")


if __name__ == '__main__':
    test_custom_mode_behavior()
