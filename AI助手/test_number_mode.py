#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试编号模式的解析功能
"""

import sys
import os
import logging
from ai_augmented_parser import AIAugmentedShipmentParser

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_number_mode():
    """测试编号模式解析"""
    print("=== 测试编号模式解析 ===\n")
    
    # 创建AI解析器实例
    try:
        parser = AIAugmentedShipmentParser()
        print("✅ AI解析器初始化成功")
    except Exception as e:
        print(f"❌ AI解析器初始化失败: {e}")
        return
    
    # 测试用例
    test_cases = [
        "七彩乐园10桶 9803 规格28",  # 主要测试用例
        "七彩乐园 10桶 9803 规格28",  # 带空格的版本
        "七彩乐园10桶 9803",  # 不带规格的版本
        "七彩乐园 9803 10桶 规格28",  # 顺序不同的版本
    ]
    
    for i, test_text in enumerate(test_cases):
        print(f"\n测试用例 {i+1}: {test_text}")
        print("-" * 80)
        
        try:
            # 使用编号模式解析
            result = parser.parse(test_text, number_mode=True)
            
            print(f"解析结果:")
            print(f"  购买单位: {result.purchase_unit}")
            print(f"  产品名称: {result.product_name}")
            print(f"  产品型号: {result.model_number}")
            print(f"  桶数: {result.quantity_tins}")
            print(f"  公斤数: {result.quantity_kg}")
            print(f"  金额: {result.amount}")
            print(f"  有效: {result.is_valid()}")
            
            # 打印产品详情
            print(f"  产品数量: {len(result.products)}")
            for j, product in enumerate(result.products):
                print(f"  产品{j+1}:")
                print(f"    名称: {product['name']}")
                print(f"    型号: {product['model_number']}")
                print(f"    桶数: {product['quantity_tins']}")
                print(f"    公斤: {product['quantity_kg']}")
                print(f"    规格: {product['tin_spec']}kg/桶")
                print(f"    单价: {product['unit_price']}")
                print(f"    金额: {product['amount']}")
                
        except Exception as e:
            print(f"❌ 解析失败: {e}")
            import traceback
            traceback.print_exc()
        
        print("-" * 80)

if __name__ == "__main__":
    test_number_mode()
