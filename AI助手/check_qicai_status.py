#!/usr/bin/env python3
# 检查七彩乐园数据库状态
import os
import sqlite3

# 检查数据库文件
db_path = os.path.join('unit_databases', '七彩乐园.db')
print(f'数据库路径: {db_path}')
print(f'文件是否存在: {os.path.exists(db_path)}')

if os.path.exists(db_path):
    print(f'文件大小: {os.path.getsize(db_path)} bytes')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查所有表
        cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
        tables = cursor.fetchall()
        print(f'\n数据库中的表:')
        for table in tables:
            print(f'  - {table[0]}')
        
        # 检查products表
        if any(t[0] == 'products' for t in tables):
            cursor.execute('SELECT COUNT(*) FROM products')
            count = cursor.fetchone()[0]
            print(f'\nProducts表状态:')
            print(f'  记录数: {count}')
            
            # 检查最后几条记录
            cursor.execute('SELECT id, model_number, name FROM products ORDER BY id DESC LIMIT 5')
            last_products = cursor.fetchall()
            print(f'  最后5个产品:')
            for product in last_products:
                print(f'    ID: {product[0]}, 型号: {product[1]}, 名称: {product[2]}')
        else:
            print('\n错误: 数据库中不存在products表!')
        
        conn.close()
        
    except Exception as e:
        print(f'\n连接数据库错误: {e}')
else:
    print('错误: 数据库文件不存在!')