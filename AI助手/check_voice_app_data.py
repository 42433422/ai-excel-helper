#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查语音应用使用的数据
"""

import sqlite3

def check_voice_app_data():
    """检查语音应用使用的数据"""
    try:
        conn = sqlite3.connect('products.db')
        cursor = conn.cursor()
        
        # 检查特定产品
        cursor.execute('SELECT * FROM products WHERE model_number = ? OR model_number = ?', ('9806A', '6824A'))
        results = cursor.fetchall()
        print('数据库中的产品数据:')
        for row in results:
            print(f'ID: {row[0]}, 型号: {row[1]}, 名称: {row[2]}, 价格: {row[3]}')
        
        # 检查产品总数
        cursor.execute('SELECT COUNT(*) FROM products')
        total = cursor.fetchone()[0]
        print(f'\n数据库中产品总数: {total}')
        
        # 检查蕊芯相关产品
        cursor.execute('SELECT * FROM products WHERE name LIKE ?', ('%蕊芯%',))
        ruixin = cursor.fetchall()
        print(f'\n蕊芯相关产品: {len(ruixin)} 个')
        
        conn.close()
        
        return True
    except Exception as e:
        print(f"检查失败: {e}")
        return False

if __name__ == "__main__":
    check_voice_app_data()
