#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3

def test_orders():
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # 检查orders表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='orders'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print('❌ orders表不存在')
            return
        
        print('✅ orders表存在')
        
        # 查看表结构
        cursor.execute("PRAGMA table_info(orders)")
        columns = cursor.fetchall()
        print('\n📋 orders表结构:')
        for col in columns:
            print(f'  {col[1]} ({col[2]})')
        
        # 统计记录数
        cursor.execute('SELECT COUNT(*) FROM orders')
        count = cursor.fetchone()[0]
        print(f'\n📊 orders表中总共有 {count} 条记录')
        
        if count > 0:
            # 查看前几条记录
            cursor.execute('SELECT * FROM orders LIMIT 5')
            records = cursor.fetchall()
            
            print('\n📄 前5条记录:')
            for i, record in enumerate(records, 1):
                print(f'  {i}. {record}')
        
        conn.close()
        
    except Exception as e:
        print(f'查询失败: {e}')

if __name__ == '__main__':
    test_orders()