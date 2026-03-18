#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复SQL语法错误
"""

def fix_sql_syntax():
    """修复SQL语法问题"""
    
    # 读取文件
    with open('shipment_parser.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找并修复有问题的SQL语句
    problematic_queries = [
        # 查找可能存在问题的JOIN语句
        ("FROM products p\nJOIN customer_products cp ON p.id = cp.product_id", 
         "FROM products p JOIN customer_products cp ON p.id = cp.product_id"),
        
        ("SELECT p.model_number, p.name, p.specification, cp.custom_price", 
         "SELECT p.model_number, p.name, p.specification, cp.custom_price"),
        
        ("SELECT p.model_number, p.name, p.specification, p.price", 
         "SELECT p.model_number, p.name, p.specification, p.price"),
    ]
    
    # 修复查询
    for old_pattern, new_pattern in problematic_queries:
        if old_pattern in content:
            content = content.replace(old_pattern, new_pattern)
            print(f"✅ 修复SQL语法: {new_pattern[:50]}...")
    
    # 保存文件
    with open('shipment_parser.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("SQL语法修复完成!")

if __name__ == "__main__":
    fix_sql_syntax()