#!/usr/bin/env python3
import sqlite3
import os

db_path = 'products_empty.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 查看所有购买单位，查找七彩乐园相关
    cursor.execute("SELECT * FROM purchase_units WHERE unit_name LIKE '%七彩%' OR unit_name LIKE '%乐园%'")
    qicai_units = cursor.fetchall()
    
    print('=== 查找七彩乐园相关单位 ===')
    if qicai_units:
        for unit in qicai_units:
            print(f'ID: {unit[0]}, 单位名: {unit[1]}, 联系人: {unit[2]}, 电话: {unit[3]}, 地址: {unit[4]}')
    else:
        print('未找到七彩乐园相关单位')
    
    # 查看所有购买单位
    cursor.execute("SELECT * FROM purchase_units")
    all_units = cursor.fetchall()
    
    print('\n=== 所有购买单位 ===')
    for unit in all_units:
        print(f'ID: {unit[0]}, 单位名: {unit[1]}, 联系人: {unit[2]}, 电话: {unit[3]}, 地址: {unit[4]}')
    
    conn.close()
else:
    print('products_empty.db 不存在')
