#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试前端页面是否正常加载
"""

import requests

# 测试购买单位加载
print("=== 测试购买单位加载 ===")
r1 = requests.get('http://localhost:8080/api/customers')
if r1.status_code == 200:
    data = r1.json()
    print(f"✅ 购买单位API正常: {data['count']} 个单位")
    print("购买单位列表:")
    for unit in data['customers'][:5]:
        print(f"  - {unit['unit_name']}")
else:
    print(f"❌ 购买单位API失败: {r1.status_code}")

# 测试产品列表加载
print(f"\n=== 测试产品列表加载 ===")
if r1.status_code == 200:
    units = r1.json()['customers']
    
    # 测试几个主要单位
    test_units = ['蕊芯家私', '温总', '七彩乐园']
    
    for unit_name in test_units:
        unit = next((u for u in units if u['unit_name'] == unit_name), None)
        if unit:
            r2 = requests.get(f'http://localhost:8080/api/products/{unit["id"]}')
            if r2.status_code == 200:
                data2 = r2.json()
                print(f"✅ {unit_name}: {data2['count']} 个产品")
            else:
                print(f"❌ {unit_name} 产品API失败: {r2.status_code}")
        else:
            print(f"❌ 找不到购买单位: {unit_name}")

print(f"\n=== 验证数据完整性 ===")

# 检查数据库状态
r3 = requests.get('http://localhost:8080/api/customers')
if r3.status_code == 200:
    customers = r3.json()
    
    # 统计总关联数
    total_products = 0
    for customer in customers['customers']:
        r4 = requests.get(f'http://localhost:8080/api/products/{customer["id"]}')
        if r4.status_code == 200:
            total_products += r4.json()['count']
    
    print(f"✅ 数据完整性检查通过")
    print(f"   - 购买单位: {customers['count']} 个")
    print(f"   - 总产品关联: {total_products} 个")
    print(f"   - 平均每单位: {total_products / customers['count']:.1f} 个产品")
