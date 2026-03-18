#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查所有客户记录
"""

import sqlite3

def check_all_customers():
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()

    print('=== 检查所有客户记录 ===')

    # 查看所有客户名称（包含蕊芯的）
    cursor.execute('SELECT id, unit_name, contact_person, is_active FROM purchase_units ORDER BY unit_name')
    customers = cursor.fetchall()

    print(f'客户总数: {len(customers)}')
    print()

    # 查找所有包含'蕊芯'的客户
    ruixin_customers = []
    for customer in customers:
        if '蕊芯' in customer[1]:
            ruixin_customers.append(customer)
            print(f'找到蕊芯客户: ID {customer[0]} - {customer[1]} (联系人: {customer[2]})')

    if not ruixin_customers:
        print('没有找到包含"蕊芯"的客户')
        print()
        print('所有客户列表:')
        for i, customer in enumerate(customers[:20]):  # 只显示前20个
            status = '启用' if customer[3] == 1 else '停用'
            print(f'{i+1:2d}. ID {customer[0]:2d} - {customer[1]:20} ({customer[2]:8}) [{status}]')
        if len(customers) > 20:
            print(f'... 还有 {len(customers) - 20} 个客户')

    # 检查是否有停用的客户
    inactive_customers = [c for c in customers if c[3] == 0]
    if inactive_customers:
        print(f'\n发现 {len(inactive_customers)} 个停用的客户:')
        for customer in inactive_customers:
            print(f'  ID {customer[0]:2d} - {customer[1]:20} ({customer[2]:8})')

    conn.close()

if __name__ == "__main__":
    check_all_customers()