#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os

def check_all_databases():
    """检查所有数据库中的数据"""
    
    databases = ['database.db', 'products.db']
    
    for db_file in databases:
        if os.path.exists(db_file):
            try:
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                
                print(f"\n📊 {db_file} 中的表:")
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                for table in tables:
                    table_name = table[0]
                    cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
                    count = cursor.fetchone()[0]
                    print(f'  - {table_name}: {count} 条记录')
                    
                    if count > 0 and count <= 10:
                        cursor.execute(f'SELECT * FROM {table_name} LIMIT 3')
                        records = cursor.fetchall()
                        print(f'    前3条记录:')
                        for i, record in enumerate(records, 1):
                            print(f'      {i}. {record}')
                
                conn.close()
                
            except Exception as e:
                print(f'\n❌ {db_file} 查询失败: {e}')
        else:
            print(f'\n❌ {db_file} 不存在')

if __name__ == '__main__':
    check_all_databases()