#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库中的所有表和数据
"""

import sqlite3

def check_all_tables():
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # 获取所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        print('数据库中的所有表:')
        for table in tables:
            table_name = table[0]
            print(f'  - {table_name}')
            
            # 检查每个表的数据量
            try:
                cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
                count = cursor.fetchone()[0]
                print(f'    数据行数: {count}')
            except Exception as e:
                print(f'    无法读取数据: {e}')
            
            # 如果是orders表，显示一些样本数据
            if table_name == 'orders' and count > 0:
                cursor.execute('SELECT * FROM orders LIMIT 3')
                samples = cursor.fetchall()
                print('    样本数据:')
                for i, sample in enumerate(samples, 1):
                    print(f'      {i}: {sample}')
            
            print()

        conn.close()
    except Exception as e:
        print(f"检查数据库失败: {e}")

if __name__ == '__main__':
    check_all_tables()
