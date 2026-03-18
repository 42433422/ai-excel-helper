#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3

def test_units():
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # 查询所有购买单位
        cursor.execute('SELECT DISTINCT purchase_unit FROM orders WHERE purchase_unit IS NOT NULL AND purchase_unit != "" ORDER BY purchase_unit')
        units = cursor.fetchall()
        
        print('📋 数据库中的购买单位列表:')
        for i, unit in enumerate(units, 1):
            print(f'{i:2d}. {unit[0]}')
        
        # 特别查找包含'蕊芯'的单位
        cursor.execute('SELECT DISTINCT purchase_unit FROM orders WHERE purchase_unit LIKE "%蕊芯%" ORDER BY purchase_unit')
        ruixin_units = cursor.fetchall()
        
        print(f'\n🔍 包含"蕊芯"的购买单位 ({len(ruixin_units)}个):')
        for unit in ruixin_units:
            print(f'  - {unit[0]}')
        
        conn.close()
        
    except Exception as e:
        print(f'查询失败: {e}')

if __name__ == '__main__':
    test_units()