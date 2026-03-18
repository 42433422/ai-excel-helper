#!/usr/bin/env python3
import sqlite3
import os

db_path = 'products_empty.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 查看所有包含"9803"或"白底"的产品
    cursor.execute("SELECT * FROM products WHERE model_number LIKE '%9803%' OR name LIKE '%白底%' ORDER BY model_number")
    products = cursor.fetchall()
    
    print('=== 查找9803或白底产品 ===')
    for product in products:
        print(f'ID: {product[0]}, 型号: {product[1]}, 名称: {product[2]}, 价格: {product[3]}, 规格: {product[4]}')
    
    # 查看购买单位信息
    cursor.execute("SELECT * FROM purchase_units")
    units = cursor.fetchall()
    
    print('\n=== 购买单位 ===')
    for unit in units:
        print(f'ID: {unit[0]}, 单位名: {unit[1]}, 联系人: {unit[2]}, 电话: {unit[3]}')
    
    conn.close()
else:
    print('products_empty.db 不存在')
