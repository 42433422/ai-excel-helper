#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试"七彩乐园一桶222A规格4"的解析问题
"""

import sys
import os
import logging
from ai_augmented_parser import AIAugmentedShipmentParser

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_222a_parse():
    """测试222A解析问题"""
    print("=== 测试 '七彩乐园一桶222A规格4' 解析 ===\n")
    
    # 创建AI解析器实例
    try:
        parser = AIAugmentedShipmentParser()
        print("✅ AI解析器初始化成功")
    except Exception as e:
        print(f"❌ AI解析器初始化失败: {e}")
        return
    
    # 测试用例
    test_text = "七彩乐园一桶222A规格4"
    
    print(f"测试文本: {test_text}")
    print("-" * 80)
    
    try:
        # 测试编号模式
        print("\n1. 测试编号模式:")
        result_number = parser.parse(test_text, number_mode=True)
        
        print(f"   解析结果:")
        print(f"   购买单位: {result_number.purchase_unit}")
        print(f"   产品名称: {result_number.product_name}")
        print(f"   产品型号: {result_number.model_number}")
        print(f"   桶数: {result_number.quantity_tins}")
        print(f"   公斤数: {result_number.quantity_kg}")
        print(f"   金额: {result_number.amount}")
        print(f"   有效: {result_number.is_valid()}")
        
        # 打印产品详情
        print(f"   产品数量: {len(result_number.products)}")
        for j, product in enumerate(result_number.products):
            print(f"   产品{j+1}:")
            print(f"     名称: {product['name']}")
            print(f"     型号: {product['model_number']}")
            print(f"     桶数: {product['quantity_tins']}")
            print(f"     公斤: {product['quantity_kg']}")
            print(f"     规格: {product['tin_spec']}kg/桶")
            print(f"     单价: {product['unit_price']}")
            print(f"     金额: {product['amount']}")
        
        # 测试普通模式
        print("\n2. 测试普通模式:")
        result_normal = parser.parse(test_text, number_mode=False)
        
        print(f"   解析结果:")
        print(f"   购买单位: {result_normal.purchase_unit}")
        print(f"   产品名称: {result_normal.product_name}")
        print(f"   产品型号: {result_normal.model_number}")
        print(f"   桶数: {result_normal.quantity_tins}")
        print(f"   公斤数: {result_normal.quantity_kg}")
        print(f"   金额: {result_normal.amount}")
        print(f"   有效: {result_normal.is_valid()}")
        
        # 打印产品详情
        print(f"   产品数量: {len(result_normal.products)}")
        for j, product in enumerate(result_normal.products):
            print(f"   产品{j+1}:")
            print(f"     名称: {product['name']}")
            print(f"     型号: {product['model_number']}")
            print(f"     桶数: {product['quantity_tins']}")
            print(f"     公斤: {product['quantity_kg']}")
            print(f"     规格: {product['tin_spec']}kg/桶")
            print(f"     单价: {product['unit_price']}")
            print(f"     金额: {product['amount']}")
        
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "-" * 80)

if __name__ == "__main__":
    test_222a_parse()
