#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复蕊芯客户
"""

import sqlite3

def fix_ruixin_customers():
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()

    print('=== 删除错误的"蕊芯 家私"客户 ===')
    
    # 先检查ID 6的客户
    cursor.execute('SELECT unit_name FROM purchase_units WHERE id = 6')
    customer = cursor.fetchone()
    if customer:
        print(f'准备删除: {customer[0]}')
        
        # 删除该客户及其相关数据
        cursor.execute('DELETE FROM customer_products WHERE unit_id = 6')
        cursor.execute('DELETE FROM purchase_units WHERE id = 6')
        print('✅ 已删除错误的"蕊芯 家私"客户')
    
    conn.commit()
    
    print('\n=== 清理后的蕊芯相关客户 ===')
    cursor.execute('SELECT id, unit_name FROM purchase_units WHERE unit_name LIKE "%蕊芯%" ORDER BY id')
    customers = cursor.fetchall()
    for customer in customers:
        print(f'ID {customer[0]}: {customer[1]}')
    
    print('\n=== 验证蕊芯家私1的产品数量 ===')
    cursor.execute('SELECT COUNT(*) FROM customer_products WHERE unit_id = 50 AND is_active = 1')
    count = cursor.fetchone()[0]
    print(f'蕊芯家私1产品数量: {count}个')
    
    conn.close()

if __name__ == "__main__":
    fix_ruixin_customers()