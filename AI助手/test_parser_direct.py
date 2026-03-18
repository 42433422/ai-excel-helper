#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接测试解析器
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shipment_parser import ShipmentParser

def test_parser_directly():
    # 测试订单文本
    order_text = "蕊芯1Pe白底漆10桶，规格28KG,24-4-8 哑光银珠:1桶，规格20Kg，PE稀释剂:1桶，规格180KG"
    
    print(f"=== 直接测试解析器 ===")
    print(f"订单文本: {order_text}")
    
    # 使用8080端口的数据库
    parser = ShipmentParser(db_path="products.db")
    
    try:
        # 解析订单
        result = parser.parse(order_text)
        
        print(f'\n✅ 解析结果:')
        print(f"  客户单位: {result.purchase_unit or '未识别'}")
        print(f"  产品数量: {len(result.products)}个")
        
        for i, product in enumerate(result.products, 1):
            print(f"\n  产品 {i}:")
            print(f"    名称: {product.get('name', '未知')}")
            print(f"    型号: {product.get('model_number', '未知')}")
            print(f"    数量: {product.get('quantity_tins', 0)}桶")
            print(f"    规格: {product.get('tin_spec', 0)}kg/桶")
            print(f"    总重量: {product.get('quantity_kg', 0)}kg")
            print(f"    单价: ¥{product.get('unit_price', 0)}")
            print(f"    金额: ¥{product.get('amount', 0)}")
        
        print(f'\n📋 汇总信息:')
        print(f"  总重量: {result.quantity_kg}kg")
        print(f"  总桶数: {result.quantity_tins}桶")
        print(f"  总金额: ¥{result.amount}")
        
        # 测试是否正确识别了"蕊芯家私1"
        if "蕊芯家私1" in result.purchase_unit or "蕊芯" in result.purchase_unit:
            print(f"\n✅ 客户识别正确!")
        else:
            print(f"\n❌ 客户识别失败: {result.purchase_unit}")
        
        # 测试是否避免了把"1"识别为编号
        model_numbers = [p.get('model_number', '') for p in result.products]
        if '1' in model_numbers:
            print(f"\n❌ 仍然把'1'识别为编号: {model_numbers}")
        else:
            print(f"\n✅ 成功避免把'1'识别为编号")
        
    except Exception as e:
        print(f'❌ 解析失败: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_parser_directly()