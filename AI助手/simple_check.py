#!/usr/bin/env python3
# 简单检查数据库表结构

import sqlite3
import os

def simple_check():
    """简单检查数据库表结构"""
    print("=== 简单检查数据库表结构 ===")
    
    try:
        # 连接数据库
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, 'products.db')
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查products表结构
        print("1. products表结构:")
        cursor.execute("PRAGMA table_info(products)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        print()
        
        # 检查purchase_units表结构
        print("2. purchase_units表结构:")
        cursor.execute("PRAGMA table_info(purchase_units)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        print()
        
        # 检查customer_products表结构
        print("3. customer_products表结构:")
        cursor.execute("PRAGMA table_info(customer_products)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        print()
        
        # 检查蕊芯家私1的产品（简化查询）
        print("4. 蕊芯家私1的产品:")
        cursor.execute("""
            SELECT p.id, p.model_number, p.name
            FROM products p
            WHERE p.purchase_unit_id = 24
            ORDER BY p.model_number
            LIMIT 10
        """)
        
        products = cursor.fetchall()
        if products:
            for product in products:
                print(f"  ID: {product[0]}, 型号: {product[1]}, 名称: {product[2]}")
        else:
            print("  没有专属产品")
        print()
        
        # 检查所有通用产品
        print("5. 通用产品示例:")
        cursor.execute("""
            SELECT p.id, p.model_number, p.name
            FROM products p
            WHERE p.purchase_unit_id IS NULL
            ORDER BY p.model_number
            LIMIT 10
        """)
        
        general_products = cursor.fetchall()
        for product in general_products:
            print(f"  ID: {product[0]}, 型号: {product[1]}, 名称: {product[2]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 数据库查询错误: {e}")

if __name__ == "__main__":
    simple_check()