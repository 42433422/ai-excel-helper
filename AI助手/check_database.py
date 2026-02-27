#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库中的订单情况
"""

import sqlite3

def check_database():
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # 检查orders表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='orders'")
        table_exists = cursor.fetchone()
        print('orders表存在:', table_exists)

        if table_exists:
            # 检查数据
            cursor.execute('SELECT COUNT(*) FROM orders')
            count = cursor.fetchone()[0]
            print('订单总数:', count)
            
            if count > 0:
                # 检查表结构
                cursor.execute('PRAGMA table_info(orders)')
                columns = cursor.fetchall()
                print('\norders表结构:')
                for col in columns:
                    print('  ', col)
                
                # 检查前几条数据的purchase_unit字段
                cursor.execute('SELECT order_number, purchase_unit FROM orders LIMIT 5')
                samples = cursor.fetchall()
                print('\n样本数据:')
                for sample in samples:
                    print('  订单号:', sample[0], '购买单位:', repr(sample[1]))
            else:
                print('订单表为空')
        else:
            print('orders表不存在')

        conn.close()
    except Exception as e:
        print(f"检查数据库失败: {e}")

if __name__ == '__main__':
    check_database()
