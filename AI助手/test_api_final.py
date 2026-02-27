#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试导入后的API
"""

import requests

# 测试客户单位
r1 = requests.get('http://localhost:8080/api/customers')
if r1.status_code == 200:
    data = r1.json()
    print(f"购买单位数量: {data['count']}")
    print("前10个单位:")
    for unit in data['customers'][:10]:
        print(f"  - {unit['unit_name']}")
else:
    print(f"API调用失败: {r1.status_code}")

# 测试一个购买单位的产品数量
units = r1.json()['customers']
if units:
    first_unit = units[0]
    unit_id = first_unit['id']
    r2 = requests.get(f'http://localhost:8080/api/products/{unit_id}')
    if r2.status_code == 200:
        data2 = r2.json()
        print(f"\n购买单位 '{first_unit['unit_name']}' 的产品数量: {data2['count']}")
        print("前3个产品:")
        for product in data2['products'][:3]:
            print(f"  - {product['model_number']}: {product['name']} - ¥{product.get('custom_price', product['price'])}")
