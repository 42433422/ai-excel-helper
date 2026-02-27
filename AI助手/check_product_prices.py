#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查产品价格信息
"""

import sqlite3

def check_product_prices():
    """检查产品价格信息"""
    
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()
    
    print("=== 检查9806产品的价格信息 ===")
    cursor.execute("""
        SELECT p.model_number, p.name, p.price, cp.custom_price 
        FROM products p 
        LEFT JOIN customer_products cp ON p.id = cp.product_id 
        WHERE p.model_number = '9806'
    """)
    products = cursor.fetchall()
    for product in products:
        print(f"产品: {product}")
    
    print("\n=== 检查9806A产品的价格信息 ===")
    cursor.execute("""
        SELECT p.model_number, p.name, p.price, cp.custom_price 
        FROM products p 
        LEFT JOIN customer_products cp ON p.id = cp.product_id 
        WHERE p.model_number = '9806A'
    """)
    products = cursor.fetchall()
    for product in products:
        print(f"产品: {product}")
    
    print("\n=== 检查蕊芯家私1的专属产品价格 ===")
    cursor.execute("""
        SELECT p.model_number, p.name, p.price, cp.custom_price 
        FROM products p 
        JOIN customer_products cp ON p.id = cp.product_id 
        WHERE cp.unit_id = 50 AND p.model_number IN ('9806', '9806A')
    """)
    ruixin_products = cursor.fetchall()
    for product in ruixin_products:
        print(f"专属产品: {product}")
    
    print("\n=== 检查customer_products表中的实际记录 ===")
    cursor.execute("""
        SELECT cp.unit_id, p.model_number, cp.custom_price 
        FROM customer_products cp 
        JOIN products p ON cp.product_id = p.id 
        WHERE p.model_number IN ('9806', '9806A')
    """)
    records = cursor.fetchall()
    for record in records:
        print(f"记录: {record}")
    
    conn.close()

if __name__ == "__main__":
    check_product_prices()