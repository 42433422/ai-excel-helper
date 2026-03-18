#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试集成后的DocumentAPIGenerator
"""

from shipment_document import DocumentAPIGenerator


def test_integrated_parser():
    """测试集成后的解析器"""
    print("=== 测试集成后的DocumentAPIGenerator ===\n")
    
    api_gen = DocumentAPIGenerator()
    
    # 测试复杂订单
    complex_order = "蕊芯家私:Pe白底漆10桶，规格28KG,24-4-8 哑光银珠:1桶，规格20Kg，PE稀释剂:1桶，规格180KG"
    print(f"测试复杂订单: {complex_order}")
    
    result = api_gen.parse_and_generate(complex_order)
    
    if result["success"]:
        print(f"\n✅ 成功生成发货单!")
        print(f"订单编号: {result['record_id']}")
        print(f"购买单位: {result['purchase_unit']['name']}")
        print(f"\n产品列表:")
        for i, product in enumerate(result['parsed_data']['products']):
            print(f"  {i+1}. {product['name']} - {product['quantity_tins']}桶, {product['quantity_kg']}kg, 规格{product['tin_spec']}kg/桶")
        print(f"\n文档信息:")
        print(f"  文件名: {result['document']['filename']}")
        print(f"  文件路径: {result['document']['filepath']}")
        print(f"  总金额: {result['document']['total_amount']}元")
    else:
        print(f"\n❌ 生成失败: {result['message']}")
        print(f"错误详情: {result['parsed_data']}")
    
    print("\n" + "="*80)
    
    # 测试简单订单
    simple_order = "七彩乐园PE白底10桶，PE稀释剂180kg1桶，PE哑光白面漆5桶"
    print(f"\n测试简单订单: {simple_order}")
    
    result = api_gen.parse_and_generate(simple_order)
    
    if result["success"]:
        print(f"\n✅ 成功生成发货单!")
        print(f"购买单位: {result['purchase_unit']['name']}")
        print(f"产品数量: {len(result['parsed_data']['products'])}")
    else:
        print(f"\n❌ 生成失败: {result['message']}")
    
    print("\n" + "="*80)


if __name__ == '__main__':
    test_integrated_parser()
