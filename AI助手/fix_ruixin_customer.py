#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复蕊芯客户问题
"""

import sqlite3

def fix_ruixin_customer():
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()

    print('=== 修复蕊芯客户问题 ===')
    
    # 检查当前的蕊芯客户状态
    cursor.execute('SELECT id, unit_name, contact_person, is_active FROM purchase_units WHERE unit_name LIKE "%蕊芯%" ORDER BY id')
    ruixin_customers = cursor.fetchall()
    
    print('当前蕊芯客户状态:')
    for customer in ruixin_customers:
        status = '活跃' if customer[3] == 1 else '已停用'
        print(f'  ID {customer[0]:2d} - {customer[1]:20} (联系人: {customer[2]:8}) [{status}]')
    
    # 重新激活原来的"蕊芯"客户（ID=1）
    print(f'\n=== 重新激活原蕊芯客户 ===')
    
    # 先检查是否需要重新激活
    cursor.execute('SELECT is_active FROM purchase_units WHERE id = 1')
    current_status = cursor.fetchone()
    
    if current_status and current_status[0] == 0:
        print('重新激活原蕊芯客户（ID=1）...')
        cursor.execute('UPDATE purchase_units SET is_active = 1 WHERE id = 1')
        print('✅ 原蕊芯客户已重新激活')
        
        # 验证激活结果
        cursor.execute('SELECT unit_name, is_active FROM purchase_units WHERE id = 1')
        updated_customer = cursor.fetchone()
        status = '活跃' if updated_customer[1] == 1 else '已停用'
        print(f'验证: {updated_customer[0]} - [{status}]')
        
        # 提交更改
        conn.commit()
        print('✅ 数据库更改已保存')
        
    else:
        print('原蕊芯客户已经是活跃状态')
    
    # 显示修复后的状态
    print(f'\n=== 修复后的状态 ===')
    cursor.execute('SELECT id, unit_name, contact_person, is_active FROM purchase_units WHERE unit_name LIKE "%蕊芯%" ORDER BY id')
    ruixin_customers_after = cursor.fetchall()
    
    for customer in ruixin_customers_after:
        status = '活跃' if customer[3] == 1 else '已停用'
        print(f'  ID {customer[0]:2d} - {customer[1]:20} (联系人: {customer[2]:8}) [{status}]')
    
    # 验证产品数据
    print(f'\n=== 验证产品数据 ===')
    for customer in ruixin_customers_after:
        cursor.execute('SELECT COUNT(*) FROM customer_products WHERE unit_id = ?', [customer[0]])
        product_count = cursor.fetchone()[0]
        status = '活跃' if customer[3] == 1 else '已停用'
        print(f'  {customer[1]} ({status}) - {product_count}个产品关联')
    
    conn.close()
    print(f'\n🎉 修复完成！')

if __name__ == "__main__":
    fix_ruixin_customer()