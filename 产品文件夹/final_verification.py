#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import pandas as pd

def final_verification():
    """最终验证干净数据库"""
    print('=== 最终验证：干净数据库统计 ===')
    
    conn = sqlite3.connect('customer_products_clean.db')
    
    # 客户信息
    customers = pd.read_sql_query('SELECT * FROM customers', conn)
    print(f'客户数量: {len(customers)}')
    if len(customers) > 0:
        c = customers.iloc[0]
        print(f'客户名称: {c["客户名称"]}')
        print(f'联系人: {c["联系人"]}')
        print(f'供应商: {c["供应商名称"]}')
    
    # 产品信息
    products = pd.read_sql_query('SELECT * FROM products', conn)
    print(f'产品种类: {len(products)}')
    
    # 统计信息
    cursor = conn.cursor()
    cursor.execute('SELECT SUM(金额) FROM products')
    total_amount = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT SUM(数量_KG) FROM products')
    total_quantity = cursor.fetchone()[0] or 0
    
    print(f'总金额: {total_amount:,.2f} 元')
    print(f'总数量: {total_quantity:,.2f} KG')
    
    # 显示前5个产品
    print('\n前5个产品:')
    for i, (_, p) in enumerate(products.head(5).iterrows()):
        print(f'{i+1}. {p["产品型号"]} - {p["产品名称"]} - 单价: {p["单价"]:.2f}')
    
    conn.close()

if __name__ == "__main__":
    final_verification()