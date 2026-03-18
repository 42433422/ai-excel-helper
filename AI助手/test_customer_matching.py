#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试客户匹配逻辑
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_customer_matching():
    """测试客户匹配逻辑"""
    try:
        from shipment_parser import ShipmentParser
        
        # 创建解析器实例
        parser = ShipmentParser(db_path="products.db")
        
        print("=== 测试客户匹配逻辑 ===")
        
        # 测试文本
        test_text = "蕊芯1Pe白底漆10桶"
        
        # 直接测试客户提取方法
        extracted_unit = parser._extract_purchase_unit(test_text)
        print(f"提取的客户: {extracted_unit}")
        
        # 测试不同的输入
        test_cases = [
            "蕊芯1需要PE白底漆",
            "蕊芯1Pe白底漆10桶",
            "蕊芯家私1需要PU三分光清面漆",
            "蕊芯家私需要PU三分光清面漆"
        ]
        
        print("\n=== 测试不同输入 ===")
        for i, text in enumerate(test_cases, 1):
            result = parser._extract_purchase_unit(text)
            print(f"测试 {i}: {text}")
            print(f"  结果: {result}")
        
        print("\n=== 完整解析测试 ===")
        order_text = "蕊芯1Pe白底漆10桶，规格28KG"
        result = parser.parse(order_text)
        
        print(f"原始订单: {order_text}")
        print(f"解析结果:")
        print(f"  客户单位: {result.purchase_unit}")
        print(f"  产品数量: {len(result.products)}")
        
        if result.products:
            for i, product in enumerate(result.products, 1):
                print(f"  产品 {i}: {product}")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_customer_matching()