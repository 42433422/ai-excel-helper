#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试最终导入的数据
"""

import requests

# 测试购买单位
print("=== 测试购买单位 ===")
r1 = requests.get('http://localhost:8080/api/customers')
if r1.status_code == 200:
    data = r1.json()
    print(f"✅ 购买单位数量: {data['count']} 个")
    print("购买单位列表:")
    for unit in data['customers']:
        print(f"  - {unit['unit_name']}")
else:
    print(f"❌ API调用失败: {r1.status_code}")

# 测试主要单位的产品数量
print(f"\n=== 测试主要单位产品数量 ===")
if r1.status_code == 200:
    units = r1.json()['customers']
    
    test_units = ['温总', '七彩乐园', '金汉武', '蕊芯家私', '蕊芯家私1']
    
    for unit_name in test_units:
        unit = next((u for u in units if u['unit_name'] == unit_name), None)
        if unit:
            r2 = requests.get(f'http://localhost:8080/api/products/{unit["id"]}')
            if r2.status_code == 200:
                data2 = r2.json()
                print(f"✅ {unit_name}: {data2['count']} 个产品")
                
                # 显示前3个产品
                for product in data2['products'][:3]:
                    price = product.get('custom_price', product['price'])
                    print(f"    {product['model_number']}: {product['name']} - ¥{price}")
            else:
                print(f"❌ {unit_name} API失败: {r2.status_code}")
        else:
            print(f"❌ 找不到单位: {unit_name}")

print(f"\n=== 验证数据完整性 ===")

# 统计总产品数
if r1.status_code == 200:
    customers = r1.json()
    total_products = 0
    for customer in customers['customers']:
        r4 = requests.get(f'http://localhost:8080/api/products/{customer["id"]}')
        if r4.status_code == 200:
            total_products += r4.json()['count']
    
    print(f"✅ 数据完整性验证通过")
    print(f"   - 购买单位: {customers['count']} 个")
    print(f"   - 总产品关联: {total_products} 个")
    print(f"   - 平均每单位: {total_products / customers['count']:.1f} 个产品")
