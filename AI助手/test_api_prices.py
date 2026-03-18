#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试API返回的价格
"""

import requests

# 测试蕊芯家私 (外价)
r1 = requests.get('http://localhost:8080/api/products/47')
print('蕊芯家私 - 前3个(外价)产品:')
products1 = r1.json()['products'][:3]
for p in products1:
    print(f"  {p['model_number']}: {p['name']} - {p.get('custom_price', p['price'])}")

print()

# 测试蕊芯家私1 (内价)
r2 = requests.get('http://localhost:8080/api/products/48')
print('蕊芯家私1 - 前3个(内价)产品:')
products2 = r2.json()['products'][:3]
for p in products2:
    print(f"  {p['model_number']}: {p['name']} - {p.get('custom_price', p['price'])}")
