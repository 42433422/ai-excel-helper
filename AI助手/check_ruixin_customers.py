#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查蕊芯客户
"""

import sqlite3

def check_ruixin_customers():
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()

    print('=== 当前蕊芯相关客户 ===')
    cursor.execute('SELECT id, unit_name FROM purchase_units WHERE unit_name LIKE "%蕊芯%" ORDER BY id')
    customers = cursor.fetchall()
    for customer in customers:
        print(f'ID {customer[0]}: {customer[1]}')

    print('\n=== 检查蕊芯家私1 ===')
    cursor.execute('SELECT COUNT(*) FROM customer_products WHERE unit_id = 50 AND is_active = 1')
    count = cursor.fetchone()[0]
    print(f'蕊芯家私1产品数量: {count}个')

    conn.close()

if __name__ == "__main__":
    check_ruixin_customers()