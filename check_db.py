#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os

# 检查数据库文件是否存在
db_path = os.path.join('产品文件夹', 'customer_products_final_corrected.db')
print(f"数据库路径: {os.path.abspath(db_path)}")
print(f"数据库文件存在: {os.path.exists(db_path)}")

if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print('数据库中的表:', [table[0] for table in tables])
        
        # 检查customers表结构
        if tables:
            for table in tables:
                table_name = table[0]
                print(f'\n{table_name}表结构:')
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                for col in columns:
                    print(f'  {col}')
        
        conn.close()
        
    except Exception as e:
        print(f'数据库连接失败: {e}')
else:
    print("数据库文件不存在，请检查路径")