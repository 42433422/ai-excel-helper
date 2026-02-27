#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试SQL错误
"""

import sqlite3

def debug_sql_error():
    """调试具体的SQL错误"""
    
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()
    
    print("=== 调试SQL错误 ===")
    
    # 测试各种可能的SQL语句
    test_queries = [
        # 测试1: 基础查询
        "SELECT p.model_number FROM products p",
        
        # 测试2: JOIN查询
        "SELECT p.model_number, p.name, cp.custom_price FROM products p JOIN customer_products cp ON p.id = cp.product_id",
        
        # 测试3: 带条件的JOIN查询
        "SELECT p.model_number FROM products p JOIN customer_products cp ON p.id = cp.product_id WHERE cp.unit_id = 50",
        
        # 测试4: 完整的客户专属产品查询
        "SELECT p.model_number, p.name, p.specification, cp.custom_price FROM products p JOIN customer_products cp ON p.id = cp.product_id WHERE cp.unit_id = ? AND cp.is_active = 1",
        
        # 测试5: 带UPPER的查询
        "SELECT p.model_number FROM products p WHERE UPPER(p.model_number) = UPPER(?)",
        
        # 测试6: 带LIKE的查询
        "SELECT p.model_number FROM products p WHERE p.name LIKE ?",
    ]
    
    for i, query in enumerate(test_queries, 1):
        try:
            if "?" in query:
                # 替换占位符
                test_query = query.replace("?", "9806")
                cursor.execute(test_query)
            else:
                cursor.execute(query)
            result = cursor.fetchone()
            print(f"✅ 查询{i}成功: {query[:50]}...")
        except Exception as e:
            print(f"❌ 查询{i}失败: {e}")
            print(f"   SQL: {query}")
    
    conn.close()

if __name__ == "__main__":
    debug_sql_error()