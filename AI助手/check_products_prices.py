#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看产品信息和价格
"""

import sqlite3
import os

def check_products_and_prices():
    """查看产品和价格信息"""
    if not os.path.exists('products.db'):
        print('products.db 文件不存在')
        return
    
    print('=== 产品价格信息 ===')
    try:
        conn = sqlite3.connect('products.db')
        cursor = conn.cursor()
        
        # 查看产品表结构和前10条数据
        print('\n--- 产品表 (products) ---')
        cursor.execute("SELECT id, model_number, name, specification, price, unit FROM products ORDER BY id LIMIT 20;")
        products = cursor.fetchall()
        
        print('产品ID | 型号 | 产品名称 | 规格 | 价格 | 单位')
        print('-' * 80)
        for product in products:
            print(f"{product[0]:4} | {product[1]:10} | {product[2]:20} | {product[3]:15} | {product[4]:8} | {product[5]:5}")
        
        # 查看价格统计
        print('\n--- 价格统计 ---')
        cursor.execute("SELECT COUNT(*), MIN(price), MAX(price), AVG(price) FROM products WHERE price > 0;")
        stats = cursor.fetchone()
        print(f'产品总数: {stats[0]}')
        print(f'最低价格: {stats[1]}')
        print(f'最高价格: {stats[2]}')
        print(f'平均价格: {stats[3]:.2f}')
        
        # 查看不同价格范围的产品分布
        print('\n--- 价格分布 ---')
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN price = 0 THEN '0元'
                    WHEN price <= 10 THEN '1-10元'
                    WHEN price <= 20 THEN '11-20元'
                    WHEN price <= 50 THEN '21-50元'
                    WHEN price <= 100 THEN '51-100元'
                    ELSE '100元以上'
                END as price_range,
                COUNT(*) as count
            FROM products 
            GROUP BY price_range
            ORDER BY MIN(price);
        """)
        distributions = cursor.fetchall()
        for dist in distributions:
            print(f'{dist[0]}: {dist[1]}个产品')
        
        # 查看采购单位（客户）信息
        print('\n--- 采购单位信息 ---')
        cursor.execute("SELECT id, unit_name, contact_person, contact_phone, discount_rate FROM purchase_units ORDER BY id LIMIT 10;")
        units = cursor.fetchall()
        
        print('ID | 单位名称 | 联系人 | 电话 | 折扣率')
        print('-' * 60)
        for unit in units:
            print(f"{unit[0]:2} | {unit[1]:15} | {unit[2]:8} | {unit[3]:15} | {unit[4]:8}")
        
        # 查看最近的发货记录
        print('\n--- 最近发货记录 ---')
        cursor.execute("""
            SELECT sr.id, pu.unit_name, sr.product_name, sr.model_number, sr.quantity_tins, sr.unit_price, sr.amount, sr.created_at
            FROM shipment_records sr
            JOIN purchase_units pu ON sr.unit_id = pu.id
            ORDER BY sr.created_at DESC LIMIT 10;
        """)
        shipments = cursor.fetchall()
        
        print('ID | 客户单位 | 产品名称 | 型号 | 数量 | 单价 | 总金额 | 创建时间')
        print('-' * 100)
        for shipment in shipments:
            print(f"{shipment[0]:2} | {shipment[1]:10} | {shipment[2]:15} | {shipment[3]:10} | {shipment[4]:6} | {shipment[5]:8} | {shipment[6]:10} | {shipment[7]:16}")
        
        conn.close()
        
    except Exception as e:
        print(f'读取数据时出错: {e}')

if __name__ == '__main__':
    check_products_and_prices()