#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据库功能：购买单位获取和产品匹配
"""

from shipment_parser import ShipmentParser
from shipment_document import ShipmentDocumentGenerator


def test_purchase_unit_retrieval():
    """测试购买单位获取"""
    print("=== 测试购买单位获取 ===")
    
    parser = ShipmentParser()
    
    # 测试从数据库加载购买单位
    purchase_units = parser._load_purchase_units_from_db()
    print(f"从数据库加载的购买单位数量: {len(purchase_units)}")
    print("购买单位列表:")
    for unit_name, unit_info in purchase_units.items():
        print(f"  - {unit_name}: 联系人={unit_info.get('contact_person', '无')}, 电话={unit_info.get('contact_phone', '无')}")
    
    # 测试提取购买单位
    test_cases = [
        "蕊芯PU哑光黑面漆20公斤",
        "七彩乐园9803 PE白底漆28KG",
        "温总编号NC50F，NC哑光清面漆3桶规格25单价14.5"
    ]
    
    print("\n测试购买单位提取:")
    for test_text in test_cases:
        unit = parser._extract_purchase_unit(test_text)
        print(f"  输入: {test_text}")
        print(f"  提取: {unit}")
        
        # 测试获取购买单位信息
        generator = ShipmentDocumentGenerator()
        unit_info = generator._get_purchase_unit_info(unit)
        print(f"  信息: 联系人={unit_info.contact_person}, 电话={unit_info.contact_phone}")
        print()


def test_product_matching():
    """测试产品匹配"""
    print("=== 测试产品匹配 ===")
    
    parser = ShipmentParser()
    
    test_cases = [
        ("PU哑光黑面漆", "蕊芯"),
        ("PE白底漆", "七彩乐园"),
        ("NC哑光清面漆", "温总")
    ]
    
    for product_text, unit_name in test_cases:
        print(f"  产品: {product_text}, 单位: {unit_name}")
        matched_product = parser._match_product_from_db(product_text, unit_name)
        if matched_product:
            print(f"  匹配成功: {matched_product['name']} (型号: {matched_product['model_number']}, 价格: {matched_product['price']})")
        else:
            print(f"  无匹配产品")
        print()


def test_full_parsing():
    """测试完整解析"""
    print("=== 测试完整解析 ===")
    
    parser = ShipmentParser()
    
    test_cases = [
        "蕊芯PU哑光黑面漆20公斤",
        "七彩乐园9803 PE白底漆28KG",
        "温总编号NC50F，NC哑光清面漆3桶规格25单价14.5"
    ]
    
    for test_text in test_cases:
        print(f"输入: {test_text}")
        result = parser.parse(test_text, custom_mode=False)
        print(f"购买单位: {result.purchase_unit}")
        print(f"产品数量: {len(result.products)}")
        for i, product in enumerate(result.products):
            print(f"产品{i+1}: {product['name']}, 型号: {product['model_number']}, 数量: {product['quantity_tins']}桶, 规格: {product['tin_spec']}kg, 单价: {product['unit_price']}, 金额: {product['amount']}")
        print()


if __name__ == '__main__':
    test_purchase_unit_retrieval()
    test_product_matching()
    test_full_parsing()
    print("测试完成！")
