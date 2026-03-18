#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证客户和产品数据的关联
"""

import sqlite3
import json

def verify_data_associations():
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()

    print('=== 验证客户产品数据关联 ===')

    # 获取所有有产品的客户
    cursor.execute('''
        SELECT DISTINCT pu.id, pu.unit_name, COUNT(cp.product_id) as product_count
        FROM purchase_units pu
        JOIN customer_products cp ON pu.id = cp.unit_id
        WHERE cp.is_active = 1 AND pu.is_active = 1
        GROUP BY pu.id, pu.unit_name
        ORDER BY product_count DESC
    ''')
    
    customers_with_products = cursor.fetchall()
    
    print(f'有产品数据的客户数量: {len(customers_with_products)}')
    print('前10个有产品的客户:')
    
    for i, (customer_id, customer_name, product_count) in enumerate(customers_with_products[:10]):
        print(f'{i+1:2d}. {customer_name} (ID: {customer_id}) - {product_count}个产品')
        
        # 验证前3个产品
        cursor.execute('''
            SELECT p.id, p.name, p.model_number, p.price
            FROM products p
            JOIN customer_products cp ON p.id = cp.product_id
            WHERE cp.unit_id = ? AND cp.is_active = 1 AND p.is_active = 1
            LIMIT 3
        ''', [customer_id])
        
        products = cursor.fetchall()
        for j, (product_id, product_name, model_number, price) in enumerate(products):
            print(f'    {j+1}. {product_name} ({model_number}) - ¥{price}')
        print()

    # 检查一个具体的客户（id=47）
    test_customer_id = 47
    print(f'=== 详细检查客户ID {test_customer_id} ===')
    
    # 检查客户是否存在
    cursor.execute('SELECT * FROM purchase_units WHERE id = ?', [test_customer_id])
    customer = cursor.fetchone()
    if customer:
        print(f'客户存在: {customer[1]}')
    else:
        print('客户不存在')
        return

    # 检查产品关联
    cursor.execute('''
        SELECT COUNT(*) FROM customer_products 
        WHERE unit_id = ? AND is_active = 1
    ''', [test_customer_id])
    association_count = cursor.fetchone()[0]
    print(f'活跃关联数量: {association_count}')
    
    if association_count > 0:
        # 获取具体的产品数据
        cursor.execute('''
            SELECT p.*, cp.custom_price
            FROM products p
            JOIN customer_products cp ON p.id = cp.product_id
            WHERE cp.unit_id = ? AND cp.is_active = 1 AND p.is_active = 1
            LIMIT 5
        ''', [test_customer_id])
        
        products = cursor.fetchall()
        print(f'实际获取到 {len(products)} 个产品')
        
        for i, product in enumerate(products):
            print(f'  {i+1}. ID:{product[0]} {product[2]} ({product[1]}) - ¥{product[4]}')

    conn.close()

def test_api_response():
    """测试API响应"""
    import urllib.request
    
    print('\n=== 测试API响应 ===')
    try:
        with urllib.request.urlopen('http://localhost:8080/api/products/47') as response:
            data = json.loads(response.read().decode())
            
            print('API响应状态:')
            print(f'  success: {data.get("success")}')
            print(f'  count: {data.get("count")}')
            print(f'  customer存在: {"customer" in data}')
            
            if "customer" in data:
                customer = data["customer"]
                print(f'  客户名称: {customer.get("unit_name")}')
            
            if "products" in data:
                products = data["products"]
                print(f'  产品数量: {len(products)}')
                if products:
                    first_product = products[0]
                    print(f'  第一个产品: {first_product.get("name")} - ¥{first_product.get("price")}')
    except Exception as e:
        print(f'API测试失败: {e}')

if __name__ == "__main__":
    verify_data_associations()
    test_api_response()