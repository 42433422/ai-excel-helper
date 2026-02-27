#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试更新后的蕊芯家私价格
"""

import requests

# 测试蕊芯家私和蕊芯家私1的价格对比
print("=== 测试蕊芯家私价格对比 ===")

# 测试购买单位
r1 = requests.get('http://localhost:8080/api/customers')
if r1.status_code == 200:
    units = r1.json()['customers']
    
    # 找到蕊芯家私和蕊芯家私1
    ruixin_units = [unit for unit in units if '蕊芯家私' in unit['unit_name']]
    
    print(f"找到 {len(ruixin_units)} 个蕊芯家私相关单位:")
    for unit in ruixin_units:
        print(f"  - {unit['unit_name']} (ID: {unit['id']})")
    
    # 测试每个单位的产品价格
    for unit in ruixin_units:
        r2 = requests.get(f'http://localhost:8080/api/products/{unit["id"]}')
        if r2.status_code == 200:
            data2 = r2.json()
            print(f"\n{unit['unit_name']} - {data2['count']} 个产品:")
            
            # 显示前5个产品的价格
            for product in data2['products'][:5]:
                price = product.get('custom_price', product['price'])
                print(f"  - {product['model_number']}: {product['name']} - ¥{price}")
        else:
            print(f"❌ {unit['unit_name']} API调用失败: {r2.status_code}")
    
    # 对比相同产品的价格
    if len(ruixin_units) == 2:
        print(f"\n=== 价格对比 (相同产品) ===")
        
        # 获取所有产品
        r2 = requests.get(f'http://localhost:8080/api/products/{ruixin_units[0]["id"]}')
        r3 = requests.get(f'http://localhost:8080/api/products/{ruixin_units[1]["id"]}')
        
        if r2.status_code == 200 and r3.status_code == 200:
            products1 = r2.json()['products']
            products2 = r3.json()['products']
            
            # 找到相同的产品进行比较
            for p1 in products1:
                for p2 in products2:
                    if p1['model_number'] == p2['model_number']:
                        price1 = p1.get('custom_price', p1['price'])
                        price2 = p2.get('custom_price', p2['price'])
                        diff = price2 - price1
                        print(f"  - {p1['model_number']}: {ruixin_units[0]['unit_name']} ¥{price1} vs {ruixin_units[1]['unit_name']} ¥{price2} (差: {diff:+.1f})")
                        break  # 只显示一次
        
else:
    print(f"❌ 购买单位API调用失败: {r1.status_code}")
