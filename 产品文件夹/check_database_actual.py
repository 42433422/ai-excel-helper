#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import sqlite3

def check_database_customers():
    """检查数据库中实际存在的客户"""
    conn = sqlite3.connect('customer_products_final_corrected.db')
    
    # 获取客户信息
    customers = pd.read_sql_query("SELECT * FROM customers", conn)
    products = pd.read_sql_query("SELECT * FROM products", conn)
    
    print("=== 数据库中实际存在的客户 ===")
    print(customers[['customer_id', '客户名称', '文件名']])
    
    print(f"\n=== 产品总数: {len(products)} ===")
    
    # 检查每个客户的产品数量
    for _, customer in customers.iterrows():
        customer_products = products[products['客户ID'] == customer['customer_id']]
        print(f"\n--- {customer['客户名称']} (产品数: {len(customer_products)}) ---")
        if len(customer_products) > 0:
            print(customer_products[['产品型号', '产品名称', '规格_KG', '单价']].head(5))
    
    conn.close()

if __name__ == "__main__":
    check_database_customers()