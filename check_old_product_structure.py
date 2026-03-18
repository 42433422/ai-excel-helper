# -*- coding: utf-8 -*-
import sqlite3

old_db = r"E:\FHD\产品文件夹\customer_products_final_corrected.db"
conn = sqlite3.connect(old_db)
cursor = conn.cursor()

# 查看 products 表的前几条记录
cursor.execute("SELECT * FROM products LIMIT 5")
rows = cursor.fetchall()

# 获取列名
cursor.execute("PRAGMA table_info(products)")
columns = [row[1] for row in cursor.fetchall()]

print('旧数据库 products 表列名:')
for i, col in enumerate(columns):
    print(f'  {i}: {col}')

print('\n前 5 条记录:')
for row in rows:
    print(f'\n记录:')
    for i, (col, val) in enumerate(zip(columns, row)):
        print(f'  {col}: {val}')

conn.close()
