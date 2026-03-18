#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单数据库测试
"""

import sqlite3
import re

def simple_database_test():
    """简单数据库测试"""
    
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()
    
    print("=== 简单数据库测试 ===")
    
    # 测试查询蕊芯家私1的产品
    print("\n1. 查询蕊芯家私1的产品:")
    cursor.execute('''
        SELECT p.model_number, p.name, p.specification, cp.custom_price
        FROM products p
        JOIN customer_products cp ON p.id = cp.product_id
        WHERE cp.unit_id = 50 AND cp.is_active = 1
        ORDER BY p.name
    ''')
    
    products = cursor.fetchall()
    print(f"找到 {len(products)} 个产品:")
    for product in products:
        print(f"  {product[0]} - {product[1]} ({product[2]}) - ¥{product[3]}")
    
    # 测试PE白底漆匹配
    print("\n2. 测试PE白底漆匹配:")
    keywords = ["PE", "白底漆", "9806"]
    
    for keyword in keywords:
        print(f"\n搜索关键词: {keyword}")
        
        # 测试精确匹配
        cursor.execute('''
            SELECT p.model_number, p.name, p.specification, cp.custom_price
            FROM products p
            JOIN customer_products cp ON p.id = cp.product_id
            WHERE cp.unit_id = 50 AND cp.is_active = 1 
            AND p.name LIKE ?
        ''', [f'%{keyword}%'])
        
        matches = cursor.fetchall()
        print(f"  精确匹配找到 {len(matches)} 个:")
        for match in matches:
            print(f"    {match[0]} - {match[1]} - ¥{match[3]}")
        
        # 测试型号匹配
        cursor.execute('''
            SELECT p.model_number, p.name, p.specification, cp.custom_price
            FROM products p
            JOIN customer_products cp ON p.id = cp.product_id
            WHERE cp.unit_id = 50 AND cp.is_active = 1 
            AND UPPER(p.model_number) = UPPER(?)
        ''', [keyword])
        
        matches = cursor.fetchall()
        print(f"  型号匹配找到 {len(matches)} 个:")
        for match in matches:
            print(f"    {match[0]} - {match[1]} - ¥{match[3]}")
    
    conn.close()

if __name__ == "__main__":
    simple_database_test()