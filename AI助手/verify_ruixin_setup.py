#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证蕊芯客户设置结果
"""

import sqlite3

def verify_ruixin_setup():
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()

    print('=== 验证蕊芯客户设置结果 ===')

    # 获取新的客户ID
    cursor.execute("SELECT id, unit_name FROM purchase_units WHERE unit_name IN ('蕊芯家私1', '蕊芯家私') ORDER BY unit_name")
    customers = cursor.fetchall()
    
    print(f'找到客户: {len(customers)}个')
    for customer in customers:
        print(f'  ID {customer[0]} - {customer[1]}')

    # 验证每个客户的产品数量和价格
    for customer_id, customer_name in customers:
        print(f'\n--- {customer_name} (ID: {customer_id}) ---')
        
        # 获取产品数量
        cursor.execute('''
            SELECT COUNT(*) FROM customer_products 
            WHERE unit_id = ? AND is_active = 1
        ''', [customer_id])
        product_count = cursor.fetchone()[0]
        print(f'产品数量: {product_count}个')
        
        if product_count > 0:
            # 获取前5个产品的详细信息
            cursor.execute('''
                SELECT p.name, p.model_number, cp.custom_price, p.specification
                FROM products p
                JOIN customer_products cp ON p.id = cp.product_id
                WHERE cp.unit_id = ? AND cp.is_active = 1
                ORDER BY p.name
                LIMIT 5
            ''', [customer_id])
            
            products = cursor.fetchall()
            print(f'前5个产品:')
            for product in products:
                print(f'  - {product[1]} ({product[0]}) ¥{product[2]} - {product[3]}')
        
        # 统计价格信息
        cursor.execute('''
            SELECT MIN(cp.custom_price), MAX(cp.custom_price), AVG(cp.custom_price)
            FROM customer_products cp
            WHERE cp.unit_id = ? AND cp.is_active = 1
        ''', [customer_id])
        
        price_stats = cursor.fetchone()
        if price_stats[0] is not None:
            print(f'价格范围: ¥{price_stats[0]:.1f} - ¥{price_stats[1]:.1f} (平均: ¥{price_stats[2]:.1f})')
        else:
            print('无价格数据')

    # 对比两个客户的价格差异
    print(f'\n=== 价格对比分析 ===')
    
    cursor.execute('''
        SELECT p.model_number, p.name,
               cp1.custom_price as inner_price,
               cp2.custom_price as outer_price,
               (cp2.custom_price - cp1.custom_price) as price_diff
        FROM products p
        JOIN customer_products cp1 ON p.id = cp1.product_id AND cp1.unit_id = 50
        JOIN customer_products cp2 ON p.id = cp2.product_id AND cp2.unit_id = 49
        WHERE cp1.is_active = 1 AND cp2.is_active = 1
        ORDER BY p.name
        LIMIT 10
    ''')
    
    price_comparisons = cursor.fetchall()
    print(f'对比结果 (前10个产品):')
    for comparison in price_comparisons:
        model, name, inner_price, outer_price, diff = comparison
        if inner_price > 0 and outer_price > 0:
            print(f'  {model} ({name})')
            print(f'    内单价: ¥{inner_price} | 外单价: ¥{outer_price} | 差价: ¥{diff:.1f}')

    conn.close()
    print(f'\n🎉 验证完成！')

if __name__ == "__main__":
    verify_ruixin_setup()