#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理蕊芯数据并重新设置客户
"""

import sqlite3

def cleanup_and_setup_ruixin():
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()

    print('=== 清理原有蕊芯数据 ===')

    # 1. 停用原有的蕊芯客户（ID=1）
    print('1. 停用原有蕊芯客户（ID=1）...')
    cursor.execute('UPDATE purchase_units SET is_active = 0 WHERE id = 1')
    print('✅ 原蕊芯客户已停用')

    # 2. 删除该客户的所有产品关联
    print('2. 删除原有产品关联...')
    cursor.execute('DELETE FROM customer_products WHERE unit_id = 1')
    deleted_count = cursor.rowcount
    print(f'✅ 已删除 {deleted_count} 个产品关联')

    # 3. 创建新的客户单位
    print('3. 创建新的客户单位...')
    
    # 蕊芯家私（外单价）
    cursor.execute('''
        INSERT INTO purchase_units (unit_name, contact_person, is_active, created_at, updated_at)
        VALUES (?, ?, 1, datetime('now'), datetime('now'))
    ''', ('蕊芯家私', '郭总'))
    ruixin_outer_id = cursor.lastrowid
    print(f'✅ 创建蕊芯家私（外单价），ID: {ruixin_outer_id}')

    # 蕊芯家私1（内单价）
    cursor.execute('''
        INSERT INTO purchase_units (unit_name, contact_person, is_active, created_at, updated_at)
        VALUES (?, ?, 1, datetime('now'), datetime('now'))
    ''', ('蕊芯家私1', '郭总'))
    ruixin_inner_id = cursor.lastrowid
    print(f'✅ 创建蕊芯家私1（内单价），ID: {ruixin_inner_id}')

    # 提交更改
    conn.commit()

    # 4. 验证结果
    print('\n=== 验证清理结果 ===')
    cursor.execute('SELECT id, unit_name, is_active FROM purchase_units WHERE unit_name LIKE "%蕊芯%" ORDER BY id')
    ruixin_customers = cursor.fetchall()
    
    for customer in ruixin_customers:
        status = '活跃' if customer[2] == 1 else '已停用'
        print(f'ID {customer[0]:2d} - {customer[1]:15} [{status}]')

    conn.close()
    print('\n🎉 清理和设置完成！')
    
    return ruixin_outer_id, ruixin_inner_id

if __name__ == "__main__":
    cleanup_and_setup_ruixin()