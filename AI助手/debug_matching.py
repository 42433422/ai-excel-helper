#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试AI解析器的数据库匹配逻辑
"""

import sqlite3
import re
from shipment_parser import ShipmentParser

def debug_database_matching():
    """调试数据库匹配逻辑"""
    
    # 创建解析器实例
    parser = ShipmentParser()
    
    # 测试文本："七彩乐园10桶9803A规格25"
    test_text = "七彩乐园10桶9803A规格25"
    
    print(f"=== 调试数据库匹配逻辑 ===")
    print(f"测试文本: {test_text}")
    print()
    
    # 1. 清理输入文本
    search_text = re.sub(r'\d+\s*(?:桶|kg|千克|公斤)', '', test_text)
    print(f"1. 清理数量信息后: '{search_text}'")
    
    # 2. 移除购买单位名称
    search_text = search_text.replace("七彩乐园", '').strip()
    print(f"2. 移除购买单位后: '{search_text}'")
    
    # 3. 提取产品关键词
    product_keywords = parser._extract_product_keywords(search_text)
    print(f"3. 提取的产品关键词: {product_keywords}")
    
    # 4. 处理关键词，提取型号
    processed_keywords = []
    for keyword in product_keywords:
        # 尝试从关键词中提取型号（数字+字母组合）
        model_match = re.search(r'\b[A-Z0-9]+\b', keyword, re.IGNORECASE)
        if model_match:
            processed_keywords.append(model_match.group(0))
        else:
            # 尝试提取纯数字型号（但排除单个数字）
            number_match = re.search(r'\b\d{2,}\b', keyword)
            if number_match:
                processed_keywords.append(number_match.group(0))
            else:
                # 保留原始关键词
                processed_keywords.append(keyword)
    
    print(f"4. 处理后的关键词（包含型号）: {processed_keywords}")
    
    # 5. 手动测试数据库查询
    print("\n5. 手动测试数据库查询:")
    
    conn = sqlite3.connect("products.db")
    cursor = conn.cursor()
    
    # 测试原始关键词
    print(f"   测试原始关键词: {product_keywords}")
    for keyword in product_keywords:
        cursor.execute("SELECT name, model_number, specification, price FROM products WHERE model_number LIKE ? OR name LIKE ?", (f'%{keyword}%', f'%{keyword}%'))
        rows = cursor.fetchall()
        print(f"     '{keyword}' 查询结果: {len(rows)} 个匹配")
        for row in rows:
            print(f"       {row}")
    
    # 测试处理后的关键词
    print(f"\n   测试处理后关键词: {processed_keywords}")
    for keyword in processed_keywords:
        cursor.execute("SELECT name, model_number, specification, price FROM products WHERE model_number LIKE ? OR name LIKE ?", (f'%{keyword}%', f'%{keyword}%'))
        rows = cursor.fetchall()
        print(f"     '{keyword}' 查询结果: {len(rows)} 个匹配")
        for row in rows:
            print(f"       {row}")
    
    # 6. 直接测试9803A
    print(f"\n6. 直接测试 '9803A':")
    cursor.execute("SELECT name, model_number, specification, price FROM products WHERE model_number LIKE '%9803A%' OR name LIKE '%9803A%'")
    rows = cursor.fetchall()
    print(f"   直接查询 '9803A': {len(rows)} 个匹配")
    for row in rows:
        print(f"     {row}")
    
    conn.close()
    
    # 7. 测试编号模式匹配
    print(f"\n7. 测试编号模式匹配:")
    result = parser._match_product_from_db(test_text, "七彩乐园", number_mode=True)
    print(f"   _match_product_from_db 结果: {result}")

if __name__ == "__main__":
    debug_database_matching()