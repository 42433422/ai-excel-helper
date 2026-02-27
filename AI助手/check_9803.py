#!/usr/bin/env python3
import sqlite3
import os

db_path = 'products.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 查看是否有9803型号的产品
    cursor.execute("SELECT * FROM products WHERE model_number LIKE '%9803%'")
    products_9803 = cursor.fetchall()
    
    print('=== 查找9803型号产品 ===')
    if products_9803:
        for product in products_9803:
            print(f'ID: {product[0]}, 型号: {product[1]}, 名称: {product[2]}, 价格: {product[3]}, 规格: {product[4]}')
    else:
        print('未找到9803型号的产品')
    
    # 查看所有包含"白底"的产品
    cursor.execute("SELECT * FROM products WHERE name LIKE '%白底%'")
    white_base_products = cursor.fetchall()
    
    print('\n=== 所有白底产品 ===')
    for product in white_base_products:
        print(f'ID: {product[0]}, 型号: {product[1]}, 名称: {product[2]}, 价格: {product[3]}, 规格: {product[4]}')
    
    conn.close()
else:
    print('数据库文件不存在')
