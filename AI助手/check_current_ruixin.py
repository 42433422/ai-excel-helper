#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查现有的蕊芯客户情况
"""

import sqlite3

def check_current_ruixin():
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()

    print('=== 检查现有蕊芯客户 ===')

    # 查看所有包含'蕊芯'的客户
    cursor.execute('SELECT id, unit_name, contact_person, is_active FROM purchase_units WHERE unit_name LIKE "%蕊芯%" ORDER BY id')
    ruixin_customers = cursor.fetchall()

    for customer in ruixin_customers:
        status = '活跃' if customer[3] == 1 else '已停用'
        print(f'ID {customer[0]:2d} - {customer[1]:20} (联系人: {customer[2]:8}) [{status}]')

    print(f'\n当前蕊芯客户总数: {len(ruixin_customers)}')

    # 检查每个客户的产品数量
    print('\n=== 产品关联统计 ===')
    for customer in ruixin_customers:
        cursor.execute('SELECT COUNT(*) FROM customer_products WHERE unit_id = ?', [customer[0]])
        product_count = cursor.fetchone()[0]
        status = '活跃' if customer[3] == 1 else '已停用'
        print(f'{customer[1]} ({status}) - {product_count}个产品关联')

    conn.close()

if __name__ == "__main__":
    check_current_ruixin()