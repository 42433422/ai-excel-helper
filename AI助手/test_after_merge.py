#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试合并后的数据
"""

import requests

# 测试购买单位数量
print("=== 测试合并后的购买单位 ===")
r1 = requests.get('http://localhost:8080/api/customers')
if r1.status_code == 200:
    data = r1.json()
    print(f"✅ 购买单位数量: {data['count']} 个 (从24个减少到21个)")
    
    # 检查是否还有金汉武相关单位
    jinhanwu_units = [unit for unit in data['customers'] if '金汉武' in unit['unit_name']]
    print(f"金汉武相关单位: {len(jinhanwu_units)} 个")
    for unit in jinhanwu_units:
        print(f"  - {unit['unit_name']}")
else:
    print(f"❌ API调用失败: {r1.status_code}")

# 测试金汉武单位的产品数量
print(f"\n=== 测试金汉武单位产品 ===")
if r1.status_code == 200:
    units = r1.json()['customers']
    jinhanwu_unit = next((u for u in units if u['unit_name'] == '金汉武'), None)
    
    if jinhanwu_unit:
        r2 = requests.get(f'http://localhost:8080/api/products/{jinhanwu_unit["id"]}')
        if r2.status_code == 200:
            data2 = r2.json()
            print(f"✅ 金汉武: {data2['count']} 个产品")
            print("前5个产品:")
            for product in data2['products'][:5]:
                price = product.get('custom_price', product['price'])
                print(f"  - {product['model_number']}: {product['name']} - ¥{price}")
        else:
            print(f"❌ 金汉武产品API失败: {r2.status_code}")
    else:
        print("❌ 找不到金汉武单位")

# 测试其他主要单位
print(f"\n=== 测试其他主要单位 ===")
test_units = ['蕊芯家私', '温总', '七彩乐园']

for unit_name in test_units:
    if r1.status_code == 200:
        unit = next((u for u in units if u['unit_name'] == unit_name), None)
        if unit:
            r2 = requests.get(f'http://localhost:8080/api/products/{unit["id"]}')
            if r2.status_code == 200:
                data2 = r2.json()
                print(f"✅ {unit_name}: {data2['count']} 个产品")
            else:
                print(f"❌ {unit_name} API失败: {r2.status_code}")
        else:
            print(f"❌ 找不到单位: {unit_name}")
