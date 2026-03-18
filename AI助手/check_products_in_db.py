#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库中的产品
"""

import sqlite3

def check_products_in_database():
    """检查数据库中是否有这些产品"""
    
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()
    
    print("=== 检查蕊芯家私1的产品 ===")
    
    # 蕊芯家私1的产品（ID 50）
    cursor.execute('''
        SELECT p.model_number, p.name, p.specification, cp.custom_price
        FROM products p
        JOIN customer_products cp ON p.id = cp.product_id
        WHERE cp.unit_id = 50 AND cp.is_active = 1
        ORDER BY p.name
        LIMIT 20
    ''')
    
    products = cursor.fetchall()
    print(f"蕊芯家私1共有 {len(products)} 个产品:")
    for product in products:
        print(f"  {product[0]} - {product[1]} ({product[2]}) - ¥{product[3]}")
    
    # 搜索PE白底漆相关产品
    print(f"\n=== 搜索PE白底漆 ===")
    cursor.execute('''
        SELECT p.model_number, p.name, p.specification, cp.custom_price
        FROM products p
        JOIN customer_products cp ON p.id = cp.product_id
        WHERE cp.unit_id = 50 AND cp.is_active = 1 
        AND (p.name LIKE '%PE白底漆%' OR p.name LIKE '%PE%' OR p.name LIKE '%白底漆%')
    ''')
    
    pe_products = cursor.fetchall()
    print(f"找到 {len(pe_products)} 个PE相关产品:")
    for product in pe_products:
        print(f"  {product[0]} - {product[1]} ({product[2]}) - ¥{product[3]}")
    
    # 搜索稀释剂产品
    print(f"\n=== 搜索稀释剂 ===")
    cursor.execute('''
        SELECT p.model_number, p.name, p.specification, cp.custom_price
        FROM products p
        JOIN customer_products cp ON p.id = cp.product_id
        WHERE cp.unit_id = 50 AND cp.is_active = 1 
        AND (p.name LIKE '%稀释剂%' OR p.name LIKE '%PE稀释剂%')
    ''')
    
    diluent_products = cursor.fetchall()
    print(f"找到 {len(diluent_products)} 个稀释剂产品:")
    for product in diluent_products:
        print(f"  {product[0]} - {product[1]} ({product[2]}) - ¥{product[3]}")
    
    # 搜索哑光银珠产品
    print(f"\n=== 搜索哑光银珠 ===")
    cursor.execute('''
        SELECT p.model_number, p.name, p.specification, cp.custom_price
        FROM products p
        JOIN customer_products cp ON p.id = cp.product_id
        WHERE cp.unit_id = 50 AND cp.is_active = 1 
        AND (p.name LIKE '%哑光%' OR p.name LIKE '%银珠%' OR p.name LIKE '%24-4-8%')
    ''')
    
    silver_products = cursor.fetchall()
    print(f"找到 {len(silver_products)} 个哑光银珠产品:")
    for product in silver_products:
        print(f"  {product[0]} - {product[1]} ({product[2]}) - ¥{product[3]}")
    
    conn.close()

if __name__ == "__main__":
    check_products_in_database()