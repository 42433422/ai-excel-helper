#!/usr/bin/env python3
# 测试完整的解析过程

import sys
import os
import re
from shipment_parser import ShipmentParser

def test_full_parsing():
    """测试完整的解析过程"""
    print("=== 测试完整的解析过程 ===")
    
    # 测试文本
    test_text = "七彩乐园10桶9803A规格25，PE稀释剂180kg1桶，PE哑光白面漆5桶规格28"
    
    print(f"测试文本: {test_text}")
    
    # 创建解析器实例
    parser = ShipmentParser()
    
    print("\n1. 测试单个产品解析:")
    # 直接测试_parse_single_product
    
    # 测试第一个产品：七彩乐园10桶9803A规格25
    product1 = "七彩乐园10桶9803A规格25"
    print(f"\n测试产品 1: {product1}")
    result1 = parser._parse_single_product(product1, is_custom=False, original_text=test_text, number_mode=True)
    print(f"解析结果: {result1}")
    
    # 测试_match_product_from_db
    print("测试_match_product_from_db:")
    purchase_unit = parser._extract_purchase_unit(test_text)
    db_match1 = parser._match_product_from_db(product1, purchase_unit, number_mode=True)
    print(f"数据库匹配结果: {db_match1}")
    
    # 直接测试9803A
    print("\n直接测试9803A:")
    db_match_direct = parser._match_product_from_db('9803A', purchase_unit, number_mode=True)
    print(f"直接匹配结果: {db_match_direct}")
    
    # 测试关键词提取
    print("\n测试关键词提取:")
    # 模拟_match_product_from_db中的关键词提取
    search_text = re.sub(r'\d+\s*(?:桶|kg|千克|公斤)', '', product1)
    # 编号模式下保留数字
    if purchase_unit:
        search_text = search_text.replace(purchase_unit, '').strip()
    print(f"清理后的文本: {search_text}")
    
    # 提取关键词
    product_keywords = parser._extract_product_keywords(search_text)
    print(f"提取的关键词: {product_keywords}")
    
    # 如果没有关键词，尝试直接从文本中提取型号
    if not product_keywords:
        # 尝试提取型号（数字+字母组合）
        model_match = re.search(r'\b[A-Z0-9]+\b', search_text, re.IGNORECASE)
        if model_match:
            print(f"提取的型号: {model_match.group(0)}")
        else:
            # 尝试提取纯数字型号（但排除单个数字）
            number_match = re.search(r'\b\d{2,}\b', search_text)
            if number_match:
                print(f"提取的数字型号: {number_match.group(0)}")
    
    print("\n2. 测试完整解析:")
    # 测试完整解析
    full_result = parser.parse(test_text, custom_mode=False, number_mode=True)
    print(f"完整解析结果: {full_result.products}")
    print(f"完整解析状态: {'成功' if full_result.products else '失败'}")
    
    print("\n3. 测试AI增强解析器:")
    # 测试AI增强解析器
    from ai_augmented_parser import AIAugmentedShipmentParser
    ai_parser = AIAugmentedShipmentParser()
    ai_result = ai_parser.parse(test_text, custom_mode=False, number_mode=True)
    print(f"AI解析结果: {ai_result.products}")
    print(f"AI解析状态: {'成功' if ai_result.products else '失败'}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_full_parsing()

