#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试名称模式的产品匹配
"""

import sys
import os

# 添加AI助手目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'AI助手'))

from shipment_parser import ShipmentParser

def test_name_mode_matching():
    """测试名称模式的产品匹配"""
    parser = ShipmentParser()
    
    # 测试订单文本
    order_text = "蕊芯Pe白底漆10桶，规格28KG,哑光银珠:1桶，规格20Kg，PE稀释剂:1桶，规格180KG"
    
    print(f"测试订单文本: {order_text}")
    print("=" * 80)
    
    # 解析订单（不启用编号模式，使用名称模式）
    parsed_order = parser.parse(order_text, number_mode=False)
    
    print(f"解析结果:")
    print(f"购买单位: {parsed_order.purchase_unit}")
    print(f"产品数量: {len(parsed_order.products)}")
    print(f"有效: {parsed_order.is_valid()}")
    print("=" * 80)
    
    # 打印每个产品的信息
    for i, product in enumerate(parsed_order.products, 1):
        print(f"\n产品 {i}:")
        print(f"  型号: {product.get('model_number', '未知')}")
        print(f"  名称: {product.get('name', '未知')}")
        print(f"  数量(kg): {product.get('quantity_kg', 0)}")
        print(f"  数量(桶): {product.get('quantity_tins', 0)}")
        print(f"  规格: {product.get('tin_spec', 0)}")
        print(f"  单价: {product.get('unit_price', 0)}")
        print(f"  金额: {product.get('amount', 0)}")
    
    print("\n" + "=" * 80)
    print("总结:")
    if parsed_order.is_valid():
        print("✅ 订单解析成功！")
        print(f"✅ 成功识别 {len(parsed_order.products)} 个产品")
    else:
        print("❌ 订单解析失败！")

if __name__ == "__main__":
    test_name_mode_matching()
