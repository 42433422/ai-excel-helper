#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试JOIN查询的条件问题
"""

import sqlite3

def test_join_conditions():
    """测试JOIN查询的条件问题"""
    
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()
    
    print("=== 测试JOIN查询的条件问题 ===")
    
    # 检查PE白底漆是否在蕊芯家私1的专属产品中
    customer_id = 50  # 蕊芯家私1
    
    # 检查这个产品是否在这个客户的专属列表中
    cursor.execute("""
        SELECT COUNT(*) 
        FROM customer_products cp 
        JOIN products p ON p.id = cp.product_id 
        WHERE cp.unit_id = ? AND p.model_number = '9806' AND cp.is_active = 1
    """, (customer_id,))
    
    count = cursor.fetchone()[0]
    print(f"PE白底漆（9806）在蕊芯家私1专属产品中: {count} 个记录")
    
    if count == 0:
        print("❌ 问题：产品不在客户专属产品列表中！")
    else:
        print("✅ 产品在客户专属产品列表中")
    
    # 测试问题查询
    print(f"\n测试问题查询:")
    
    try:
        # 这个查询应该会成功
        cursor.execute("""
            SELECT p.model_number, p.name, p.specification, cp.custom_price
            FROM products p
            JOIN customer_products cp ON p.id = cp.product_id
            WHERE cp.unit_id = ? AND UPPER(p.model_number) = UPPER(?) AND cp.is_active = 1
            LIMIT 1
        """, (customer_id, "9806"))
        
        result = cursor.fetchone()
        print(f"✅ JOIN查询成功: {result}")
        
    except Exception as e:
        print(f"❌ JOIN查询失败: {e}")
    
    # 测试可能的问题：查询一个不在专属列表中的产品
    print(f"\n测试查询一个不在专属列表中的产品:")
    
    try:
        cursor.execute("""
            SELECT p.model_number, p.name, p.specification, cp.custom_price
            FROM products p
            JOIN customer_products cp ON p.id = cp.product_id
            WHERE cp.unit_id = ? AND UPPER(p.model_number) = UPPER(?) AND cp.is_active = 1
            LIMIT 1
        """, (customer_id, "不存在的产品"))
        
        result = cursor.fetchone()
        print(f"✅ 不存在产品的查询: {result}")
        
    except Exception as e:
        print(f"❌ 不存在产品的查询失败: {e}")
    
    # 测试LEFT JOIN是否更好
    print(f"\n测试LEFT JOIN:")
    
    try:
        cursor.execute("""
            SELECT p.model_number, p.name, p.specification, cp.custom_price
            FROM products p
            LEFT JOIN customer_products cp ON p.id = cp.product_id AND cp.unit_id = ? AND cp.is_active = 1
            WHERE p.model_number = '9806'
            LIMIT 1
        """, (customer_id,))
        
        result = cursor.fetchone()
        print(f"✅ LEFT JOIN查询成功: {result}")
        
    except Exception as e:
        print(f"❌ LEFT JOIN查询失败: {e}")
    
    conn.close()

if __name__ == "__main__":
    test_join_conditions()