#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查数据库中的蕊芯家私产品"""

import sqlite3

# 连接数据库
conn = sqlite3.connect('products.db')
cursor = conn.cursor()

print('='*60)
print('检查数据库中的蕊芯家私相关数据')
print('='*60)
print()

# 1. 检查购买单位
print('1. 购买单位信息：')
cursor.execute('SELECT id, unit_name, contact_person FROM purchase_units WHERE unit_name LIKE ?', ('%蕊芯%',))
units = cursor.fetchall()

for unit in units:
    print(f'   ID: {unit[0]}, 名称: {unit[1]}, 联系人: {unit[2]}')

print()

# 2. 检查白底漆相关产品
print('2. 白底漆相关产品：')
cursor.execute('SELECT model_number, name, price FROM products WHERE name LIKE ? AND is_active = 1 LIMIT 10', ('%白底漆%',))
primers = cursor.fetchall()

for p in primers:
    print(f'   {p[0]} - {p[1]} - ¥{p[2]}/kg')

print()

# 3. 检查稀释剂相关产品
print('3. 稀释剂相关产品：')
cursor.execute('SELECT model_number, name, price FROM products WHERE name LIKE ? AND is_active = 1 LIMIT 10', ('%稀释剂%',))
diluents = cursor.fetchall()

for d in diluents:
    print(f'   {d[0]} - {d[1]} - ¥{d[2]}/kg')

print()

# 4. 检查哑光相关产品
print('4. 哑光相关产品：')
cursor.execute('SELECT model_number, name, price FROM products WHERE name LIKE ? AND is_active = 1 LIMIT 10', ('%哑光%',))
matte = cursor.fetchall()

for m in matte:
    print(f'   {m[0]} - {m[1]} - ¥{m[2]}/kg')

print()

# 5. 检查银珠相关产品
print('5. 银珠相关产品：')
cursor.execute('SELECT model_number, name, price FROM products WHERE name LIKE ? AND is_active = 1 LIMIT 10', ('%银珠%',))
silver = cursor.fetchall()

for s in silver:
    print(f'   {s[0]} - {s[1]} - ¥{s[2]}/kg')

print()
print('='*60)
print('解析问题分析')
print('='*60)

order = '蕊芯家私:Pe白底漆10桶，规格28KG,24-4-8 哑光银珠:1桶，规格20Kg，PE稀释剂:1桶，规格180KG'
print(f'\n订单：{order}')
print()
print('可能的问题：')
print('1. 订单格式特殊，包含冒号和中文逗号')
print('2. "规格"关键字被误识别为产品')
print('3. 产品名称包含特殊字符')
print('4. "24-4-8 哑光银珠"可能在数据库中不存在')

conn.close()