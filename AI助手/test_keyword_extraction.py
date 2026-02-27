#!/usr/bin/env python3
# 测试关键词提取功能

import sys
import os
from shipment_parser import ShipmentParser

def test_keyword_extraction():
    """测试关键词提取功能"""
    print("=== 测试关键词提取功能 ===")
    
    # 创建解析器实例
    parser = ShipmentParser()
    
    # 测试文本
    test_texts = [
        "9803A规格25",
        "七彩乐园10桶9803A规格25",
        "9803A",
        "PE稀释剂180kg",
        "PE哑光白面漆5桶规格28"
    ]
    
    for text in test_texts:
        print(f"\n测试文本: {text}")
        keywords = parser._extract_product_keywords(text)
        print(f"提取的关键词: {keywords}")
    
    # 测试_match_product_from_db
    print("\n=== 测试_match_product_from_db ===")
    
    # 测试9803A规格25
    result1 = parser._match_product_from_db("9803A规格25", number_mode=True)
    print(f"测试 '9803A规格25': {result1}")
    
    # 测试9803A
    result2 = parser._match_product_from_db("9803A", number_mode=True)
    print(f"测试 '9803A': {result2}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_keyword_extraction()
