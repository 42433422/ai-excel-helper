#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析蕊芯客户数据
"""

import sqlite3

def analyze_ruixin_customers():
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()

    print('=== 蕊芯客户详细分析 ===')

    # 查看所有蕊芯客户（包括停用的）
    cursor.execute('SELECT id, unit_name, contact_person, is_active FROM purchase_units WHERE unit_name LIKE "%蕊芯%" ORDER BY id')
    ruixin_customers = cursor.fetchall()

    for customer in ruixin_customers:
        status = '活跃' if customer[3] == 1 else '已停用'
        print(f'ID {customer[0]:2d} - {customer[1]:20} (联系人: {customer[2]:8}) [{status}]')

    print(f'\n蕊芯客户总数: {len(ruixin_customers)}')
    active_count = sum(1 for c in ruixin_customers if c[3] == 1)
    inactive_count = sum(1 for c in ruixin_customers if c[3] == 0)
    print(f'活跃客户: {active_count}个')
    print(f'停用客户: {inactive_count}个')

    # 检查这些客户的产品数据
    print('\n=== 蕊芯客户的产品数据 ===')
    for customer in ruixin_customers:
        cursor.execute('SELECT COUNT(*) FROM customer_products WHERE unit_id = ?', [customer[0]])
        product_count = cursor.fetchone()[0]
        status = '活跃' if customer[3] == 1 else '已停用'
        print(f'{customer[1]} ({status}) - {product_count}个产品')

    conn.close()

if __name__ == "__main__":
    analyze_ruixin_customers()