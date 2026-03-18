#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3

def check_database_structure():
    try:
        # 检查当前数据库结构
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # 查看orders表结构
        cursor.execute('PRAGMA table_info(orders)')
        columns = cursor.fetchall()
        print('📋 orders表结构:')
        for col in columns:
            print(f'  {col[1]} ({col[2]})')

        # 查看是否有其他表存储产品信息
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f'\n📊 所有表: {[t[0] for t in tables]}')

        conn.close()

    except Exception as e:
        print(f'查询失败: {e}')

if __name__ == '__main__':
    check_database_structure()