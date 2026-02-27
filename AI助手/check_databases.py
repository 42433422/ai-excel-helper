#!/usr/bin/env python3
import sqlite3
import os
import glob

# 查找所有可能的数据库文件
print('=== 查找数据库文件 ===')
db_files = glob.glob('*.db')
for db_file in db_files:
    print(f'找到数据库文件: {db_file}')

# 查找七彩乐园相关的数据库文件
print('\n=== 查找七彩乐园相关文件 ===')
qicai_files = glob.glob('*七彩*')
for file in qicai_files:
    print(f'找到文件: {file}')

# 检查当前目录中的数据库
for db_file in db_files:
    print(f'\n=== 检查数据库: {db_file} ===')
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # 查看所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f'表: {tables}')
        
        if tables:
            # 查看第一个表的内容
            first_table = tables[0][0]
            cursor.execute(f"SELECT * FROM {first_table} LIMIT 5")
            sample_data = cursor.fetchall()
            print(f'表 {first_table} 的示例数据: {sample_data}')
        
        conn.close()
    except Exception as e:
        print(f'读取数据库 {db_file} 时出错: {e}')
