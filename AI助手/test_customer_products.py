#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试客户产品数据
"""

import json
import urllib.request

def test_customer_products():
    try:
        # 获取客户列表
        with urllib.request.urlopen('http://localhost:8080/api/customers') as response:
            customers_data = json.loads(response.read().decode())
            print('所有客户:')
            for i, customer in enumerate(customers_data['customers'][:10]):
                print(f'{i+1:2d}. {customer["unit_name"]} (ID: {customer["id"]})')
            
            # 查找七彩乐园
            for customer in customers_data['customers']:
                if '七彩乐园' in customer['unit_name']:
                    print(f'\n找到七彩乐园客户: {customer["unit_name"]} (ID: {customer["id"]})')
                    with urllib.request.urlopen(f'http://localhost:8080/api/products/{customer["id"]}') as product_response:
                        products_data = json.loads(product_response.read().decode())
                        print(f'七彩乐园产品数量: {products_data.get("count", 0)}')
                        if products_data['products']:
                            print('前3个产品:')
                            for i, product in enumerate(products_data['products'][:3]):
                                print(f'  {i+1}. {product["name"]} - ¥{product["price"]}')
                    break
            
            # 测试蕊芯
            for customer in customers_data['customers']:
                if '蕊芯' in customer['unit_name']:
                    print(f'\n找到蕊芯客户: {customer["unit_name"]} (ID: {customer["id"]})')
                    with urllib.request.urlopen(f'http://localhost:8080/api/products/{customer["id"]}') as product_response:
                        products_data = json.loads(product_response.read().decode())
                        print(f'蕊芯产品数量: {products_data.get("count", 0)}')
                        if products_data['products']:
                            print('前3个产品:')
                            for i, product in enumerate(products_data['products'][:3]):
                                print(f'  {i+1}. {product["name"]} - ¥{product["price"]}')
                    break
    except Exception as e:
        print('请求失败:', str(e))

if __name__ == "__main__":
    test_customer_products()