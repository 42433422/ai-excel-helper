#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库结构和产品信息
"""

import sqlite3

def check_database_structure():
    """检查数据库结构"""
    try:
        db_path = '产品文件夹/customer_products_final_corrected.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"连接数据库: {db_path}")
        print("=" * 60)
        
        # 检查数据库表
        cursor.execute('SELECT name FROM sqlite_master WHERE type="table";')
        tables = cursor.fetchall()
        print("数据库表:")
        for table in tables:
            print(f"  - {table[0]}")
        
        print("\n" + "=" * 60)
        
        # 检查products表结构
        cursor.execute('PRAGMA table_info(products);')
        product_columns = cursor.fetchall()
        print("products表结构:")
        for column in product_columns:
            print(f"  - {column[1]} ({column[2]})")
        
        print("\n" + "=" * 60)
        
        # 检查customers表结构
        cursor.execute('PRAGMA table_info(customers);')
        customer_columns = cursor.fetchall()
        print("customers表结构:")
        for column in customer_columns:
            print(f"  - {column[1]} ({column[2]})")
        
        print("\n" + "=" * 60)
        
        # 检查产品数量
        cursor.execute('SELECT COUNT(*) FROM products;')
        product_count = cursor.fetchone()[0]
        print(f"产品总数: {product_count}")
        
        # 检查客户数量
        cursor.execute('SELECT COUNT(*) FROM customers;')
        customer_count = cursor.fetchone()[0]
        print(f"客户总数: {customer_count}")
        
        print("\n" + "=" * 60)
        
        # 搜索包含9806的产品
        cursor.execute('SELECT 产品型号, 产品名称, 规格_KG, 单价 FROM products WHERE 产品型号 LIKE "%9806%" LIMIT 10;')
        products_9806 = cursor.fetchall()
        print("包含9806的产品:")
        if products_9806:
            for product in products_9806:
                print(f"  - 型号: {product[0]}, 名称: {product[1]}, 规格: {product[2]}, 单价: {product[3]}")
        else:
            print("  无")
        
        print("\n" + "=" * 60)
        
        # 检查蕊芯客户信息
        cursor.execute('SELECT customer_id, 客户名称, 联系人, 电话 FROM customers WHERE 客户名称 LIKE "%蕊芯%" LIMIT 5;')
        ruixin_customers = cursor.fetchall()
        print("蕊芯客户信息:")
        if ruixin_customers:
            for customer in ruixin_customers:
                print(f"  - ID: {customer[0]}, 名称: {customer[1]}, 联系人: {customer[2]}, 电话: {customer[3]}")
        else:
            print("  无")
        
        conn.close()
        
    except Exception as e:
        print(f"检查数据库失败: {e}")
        import traceback
        traceback.print_exc()

def search_product_by_model(model_number):
    """根据型号搜索产品"""
    try:
        db_path = '产品文件夹/customer_products_final_corrected.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"\n搜索产品型号: {model_number}")
        print("=" * 60)
        
        # 精确匹配
        cursor.execute('SELECT 产品型号, 产品名称, 规格_KG, 单价 FROM products WHERE 产品型号 = ? LIMIT 5;', (model_number,))
        exact_matches = cursor.fetchall()
        
        if exact_matches:
            print("精确匹配:")
            for product in exact_matches:
                print(f"  - 型号: {product[0]}, 名称: {product[1]}, 规格: {product[2]}, 单价: {product[3]}")
        else:
            print("无精确匹配")
        
        # 模糊匹配
        cursor.execute('SELECT 产品型号, 产品名称, 规格_KG, 单价 FROM products WHERE 产品型号 LIKE ? LIMIT 5;', (f"%{model_number}%",))
        fuzzy_matches = cursor.fetchall()
        
        if fuzzy_matches:
            print("\n模糊匹配:")
            for product in fuzzy_matches:
                print(f"  - 型号: {product[0]}, 名称: {product[1]}, 规格: {product[2]}, 单价: {product[3]}")
        else:
            print("无模糊匹配")
        
        conn.close()
        
    except Exception as e:
        print(f"搜索产品失败: {e}")

if __name__ == '__main__':
    check_database_structure()
    search_product_by_model('9806')
    search_product_by_model('9806a')
