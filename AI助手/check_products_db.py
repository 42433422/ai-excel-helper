#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3

conn = sqlite3.connect('products.db')
cursor = conn.cursor()

# 检查表结构
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = cursor.fetchall()
print('products.db 中的表:')
for table in tables:
    print(f'  {table[0]}')

# 检查 products 表
cursor.execute('SELECT * FROM products LIMIT 5')
rows = cursor.fetchall()
print('\nproducts 表示例数据:')
for row in rows:
    print(f'  {row}')

# 搜索 9803A
cursor.execute("SELECT name, model_number, specification, price FROM products WHERE model_number LIKE '%9803A%' OR name LIKE '%9803A%'")
rows = cursor.fetchall()
print('\n搜索 9803A 的结果:')
if rows:
    for row in rows:
        print(f'  {row}')
else:
    print('  没有找到包含 9803A 的产品')

# 搜索 PE 白底漆
cursor.execute("SELECT name, model_number, specification, price FROM products WHERE name LIKE '%PE%白底漆%' OR name LIKE '%白底漆%'")
rows = cursor.fetchall()
print('\n搜索 PE白底漆 的结果:')
if rows:
    for row in rows:
        print(f'  {row}')
else:
    print('  没有找到 PE白底漆 相关产品')

conn.close()