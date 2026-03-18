#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3

def check_all_tables():
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print('📋 数据库中的所有表:')
        for table in tables:
            table_name = table[0]
            print(f'  - {table_name}')
            
            # 查看每个表的记录数
            try:
                cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
                count = cursor.fetchone()[0]
                print(f'    📊 记录数: {count}')
                
                if count > 0 and count <= 10:  # 只显示少量记录
                    cursor.execute(f'SELECT * FROM {table_name} LIMIT 3')
                    records = cursor.fetchall()
                    print(f'    📄 前3条记录:')
                    for i, record in enumerate(records, 1):
                        print(f'      {i}. {record}')
                elif count > 10:
                    print(f'    📄 记录较多，不显示详细内容')
                    
            except Exception as e:
                print(f'    ❌ 查询表 {table_name} 失败: {e}')
        
        # 特别检查包含"蕊芯"的记录
        print('\n🔍 搜索包含"蕊芯"的记录:')
        for table in tables:
            table_name = table[0]
            try:
                # 获取表结构
                cursor.execute(f'PRAGMA table_info({table_name})')
                columns = cursor.fetchall()
                text_columns = [col[1] for col in columns if col[2].upper() in ['TEXT', 'VARCHAR']]
                
                if text_columns:
                    # 搜索文本列
                    conditions = []
                    for col in text_columns:
                        conditions.append(f"{col} LIKE '%蕊芯%'")
                    
                    if conditions:
                        query = f"SELECT * FROM {table_name} WHERE {' OR '.join(conditions)} LIMIT 5"
                        cursor.execute(query)
                        records = cursor.fetchall()
                        
                        if records:
                            print(f'  📄 表 {table_name} 中的蕊芯记录:')
                            for record in records:
                                print(f'    {record}')
                                
            except Exception as e:
                continue
        
        conn.close()
        
    except Exception as e:
        print(f'查询失败: {e}')

if __name__ == '__main__':
    check_all_tables()