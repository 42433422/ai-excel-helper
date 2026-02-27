#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('unit_databases/七彩乐园.db')
cursor = conn.cursor()

# 搜索PE白底漆相关产品
sql = "SELECT model_number, name, price FROM products WHERE name LIKE '%白底%' ORDER BY name"
cursor.execute(sql)
products = cursor.fetchall()
print('七彩乐园数据库中的白底漆产品:')
for p in products:
    print(f'  型号: {p[0]:15} 名称: {p[1]:40} 价格: {p[2]}')

# 搜索PE稀释剂相关产品
sql = "SELECT model_number, name, price FROM products WHERE name LIKE '%稀释剂%' ORDER BY name"
cursor.execute(sql)
products = cursor.fetchall()
print('\n七彩乐园数据库中的稀释剂产品:')
for p in products:
    print(f'  型号: {p[0]:15} 名称: {p[1]:40} 价格: {p[2]}')

# 搜索9803型号的产品
sql = "SELECT model_number, name, price FROM products WHERE model_number LIKE '%9803%' ORDER BY name"
cursor.execute(sql)
products = cursor.fetchall()
print('\n七彩乐园数据库中的9803型号产品:')
for p in products:
    print(f'  型号: {p[0]:15} 名称: {p[1]:40} 价格: {p[2]}')

conn.close()
