#!/usr/bin/env python3
import sqlite3
import os

db_path = 'products.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 查看所有产品
    query = "SELECT DISTINCT model_number, name FROM products WHERE name LIKE '%PE%' OR name LIKE '%白底%' OR name LIKE '%稀释剂%' ORDER BY name"
    cursor.execute(query)
    products = cursor.fetchall()
    
    print('=== 数据库中的PE相关产品 ===')
    for product in products:
        print(f'型号: {product[0]}, 名称: {product[1]}')
    
    conn.close()
else:
    print('数据库文件不存在')
