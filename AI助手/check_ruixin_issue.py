#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查数据库中的产品，分析解析失败原因"""

import sqlite3
import re
from typing import List, Dict

# 检查数据库中的蕊芯家私产品
def check_ruixin_products():
    """检查数据库中的蕊芯家私产品"""
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()
    
    print('='*60)
    print('检查数据库中的蕊芯家私产品')
    print('='*60)
    print()
    
    # 1. 检查购买单位
    print('1. 检查购买单位：')
    cursor.execute('SELECT id, unit_name, contact_person FROM purchase_units WHERE unit_name LIKE ?', ('%蕊芯%',))
    units = cursor.fetchall()
    
    for unit in units:
        print(f'   ID: {unit[0]}, 名称: {unit[1]}, 联系人: {unit[2]}')
    
    print()
    
    # 2. 检查产品
    print('2. 检查产品：')
    products_to_check = ['白底漆', '哑光银珠', '稀释剂', 'Pe白底漆', 'PE稀释剂']
    
    for product_name in products_to_check:
        cursor.execute('''
            SELECT id, model_number, name, price
            FROM products 
            WHERE name LIKE ? AND is_active = 1
            LIMIT 10
        ''', (f'%{product_name}%',))
        
        products = cursor.fetchall()
        if products:
            print(f'   {product_name} 相关产品：')
            for p in products[:5]:
                print(f'     {p[1]} - {p[2]} - ¥{p[3]}/kg')
            if len(products) > 5:
                print(f'     ... 共 {len(products)} 个产品')
        else:
            print(f'   ❌ 未找到 {product_name} 相关产品')
    
    print()
    
    # 3. 检查客户产品关联
    print('3. 检查客户产品关联：')
    for unit in units:
        unit_id = unit[0]
        cursor.execute('''
            SELECT p.model_number, p.name, p.price
            FROM products p
            JOIN customer_products cp ON p.id = cp.product_id
            WHERE cp.unit_id = ? AND p.is_active = 1 AND cp.is_active = 1
            LIMIT 10
        ''', (unit_id,))
        
        customer_products = cursor.fetchall()
        if customer_products:
            print(f'   {unit[1]} 的关联产品：')
            for cp in customer_products[:5]:
                print(f'     {cp[0]} - {cp[1]} - ¥{cp[2]}/kg')
            if len(customer_products) > 5:
                print(f'     ... 共 {len(customer_products)} 个产品')
        else:
            print(f'   ❌ {unit[1]} 没有关联产品')
    
    conn.close()
    
    print()
    print('='*60)
    print('分析解析失败原因')
    print('='*60)
    
    # 分析订单格式
    order_text = '蕊芯家私:Pe白底漆10桶，规格28KG,24-4-8 哑光银珠:1桶，规格20Kg，PE稀释剂:1桶，规格180KG'
    print(f'\n订单：{order_text}')
    
    # 检查产品匹配
    print('\n4. 产品匹配分析：')
    
    # 提取产品名称
    product_names = ['Pe白底漆', '24-4-8 哑光银珠', 'PE稀释剂']
    for product in product_names:
        print(f'   {product}：')
        print(f'     格式：{product}')
        print(f'     小写：{product.lower()}')
        print(f'     无空格：{re.sub(r"\s+", "", product)}')
    
    # 检查格式问题
    print('\n5. 格式问题分析：')
    print('   - 订单包含冒号和逗号，可能导致错误分割')
    print('   - "规格"关键字被当成独立产品')
    print('   - 产品名称包含特殊字符')

if __name__ == "__main__":
    check_ruixin_products()