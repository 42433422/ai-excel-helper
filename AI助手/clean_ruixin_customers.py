#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理蕊芯客户，只保留需要的两个
"""

import sqlite3

def clean_ruixin_customers():
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()

    print('=== 清理多余的蕊芯客户 ===')
    
    # 要删除的客户ID
    delete_ids = [1, 5]  # ID 1: 蕊芯, ID 5: 蕊芯家私测试更新
    
    for delete_id in delete_ids:
        # 获取客户名称
        cursor.execute('SELECT unit_name FROM purchase_units WHERE id = ?', (delete_id,))
        customer = cursor.fetchone()
        if customer:
            customer_name = customer[0]
            print(f'准备删除: ID {delete_id} - {customer_name}')
            
            # 删除该客户及其相关数据
            cursor.execute('DELETE FROM customer_products WHERE unit_id = ?', (delete_id,))
            cursor.execute('DELETE FROM purchase_units WHERE id = ?', (delete_id,))
            print(f'✅ 已删除: {customer_name}')
    
    conn.commit()
    
    print('\n=== 清理后的蕊芯相关客户 ===')
    cursor.execute('SELECT id, unit_name FROM purchase_units WHERE unit_name LIKE "%蕊芯%" ORDER BY id')
    customers = cursor.fetchall()
    for customer in customers:
        print(f'ID {customer[0]}: {customer[1]}')
    
    print('\n=== 验证产品数量 ===')
    for customer_id, customer_name in customers:
        cursor.execute('SELECT COUNT(*) FROM customer_products WHERE unit_id = ? AND is_active = 1', (customer_id,))
        count = cursor.fetchone()[0]
        print(f'{customer_name}: {count}个产品')
    
    conn.close()

if __name__ == "__main__":
    clean_ruixin_customers()