#!/usr/bin/env python3
# 测试特定文本的编号模式解析功能

import sys
import os
from shipment_parser import ShipmentParser
from ai_augmented_parser import AIAugmentedShipmentParser

def test_specific_text():
    """测试特定文本的编号模式解析功能"""
    print("=== 测试特定文本的编号模式解析功能 ===")
    
    # 用户提供的测试文本
    test_text = "1桶，24-4-8规格25"
    
    print(f"测试文本: '{test_text}'")
    print(f"文本长度: {len(test_text)}")
    print(f"是否包含逗号: {'是' if '，' in test_text or ',' in test_text else '否'}")
    print()
    
    # 1. 传统解析器测试
    print("1. 使用传统解析器测试:")
    parser = ShipmentParser()
    
    # 非编号模式
    print("  非编号模式:")
    result_normal = parser.parse(test_text, custom_mode=False, number_mode=False)
    print(f"  解析结果: {result_normal.products}")
    print(f"  解析状态: {'成功' if result_normal.products else '失败'}")
    print()
    
    # 编号模式
    print("  编号模式:")
    result_number = parser.parse(test_text, custom_mode=False, number_mode=True)
    print(f"  解析结果: {result_number.products}")
    print(f"  解析状态: {'成功' if result_number.products else '失败'}")
    print()
    
    # 2. AI增强解析器测试
    print("2. 使用AI增强解析器测试:")
    ai_parser = AIAugmentedShipmentParser()
    
    # 非编号模式
    print("  非编号模式:")
    ai_result_normal = ai_parser.parse(test_text, custom_mode=False, number_mode=False)
    print(f"  解析结果: {ai_result_normal.products}")
    print(f"  解析状态: {'成功' if ai_result_normal.products else '失败'}")
    print()
    
    # 编号模式
    print("  编号模式:")
    ai_result_number = ai_parser.parse(test_text, custom_mode=False, number_mode=True)
    print(f"  解析结果: {ai_result_number.products}")
    print(f"  解析状态: {'成功' if ai_result_number.products else '失败'}")
    print()
    
    # 3. 对比分析
    print("3. 对比分析:")
    print(f"传统解析器 - 非编号模式产品数量: {len(result_normal.products)}")
    print(f"传统解析器 - 编号模式产品数量: {len(result_number.products)}")
    print(f"AI解析器 - 非编号模式产品数量: {len(ai_result_normal.products)}")
    print(f"AI解析器 - 编号模式产品数量: {len(ai_result_number.products)}")
    print()
    
    # 4. 详细输出产品信息
    if result_number.products:
        print("4. 编号模式下详细产品信息:")
        for i, product in enumerate(result_number.products, 1):
            print(f"  产品 {i}:")
            for key, value in product.items():
                print(f"    {key}: {value}")
            print()
    
    print("=== 测试完成 ===")

if __name__ == "__main__":
    test_specific_text()