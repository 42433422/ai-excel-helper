#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
强制刷新和清理前端缓存
"""

import requests
import json

def test_with_no_cache():
    """测试时禁用缓存"""
    try:
        # 模拟禁用缓存的请求
        headers = {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
        
        print("=== 禁用缓存测试API ===")
        
        # 测试获取购买单位
        r1 = requests.get('http://localhost:8080/api/customers', headers=headers)
        if r1.status_code == 200:
            data = r1.json()
            print(f"✅ 获取购买单位成功: {data['count']} 个")
            
            # 找到所有单位并测试产品
            for unit in data['customers'][:5]:  # 只测试前5个单位
                r2 = requests.get(f'http://localhost:8080/api/products/{unit["id"]}', headers=headers)
                if r2.status_code == 200:
                    data2 = r2.json()
                    print(f"✅ {unit['unit_name']}: {data2['count']} 个产品")
                    
                    # 检查前2个产品的格式
                    for i, product in enumerate(data2['products'][:2]):
                        name = product.get('name', '')
                        model = product.get('model_number', '')
                        print(f"   {i+1}. {model}: {name}")
                        
                        # 检查是否有异常格式
                        if any(keyword in name for keyword in ['桶', 'KG', ',', '规格']):
                            print(f"      ⚠️ 发现异常格式: {repr(name)}")
                    
                    if data2['count'] > 0:
                        break  # 找到一个有产品的单位就停止
                else:
                    print(f"❌ {unit['unit_name']}: API失败 {r2.status_code}")
        else:
            print(f"❌ 获取购买单位失败: {r1.status_code}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def test_specific_ruixin():
    """专门测试蕊芯家私的数据"""
    try:
        print("\n=== 专门测试蕊芯家私 ===")
        
        # 获取蕊芯家私
        r1 = requests.get('http://localhost:8080/api/customers')
        if r1.status_code == 200:
            data = r1.json()
            ruixin_units = [u for u in data['customers'] if '蕊芯' in u['unit_name']]
            
            for ruixin_unit in ruixin_units:
                print(f"\n测试 {ruixin_unit['unit_name']}:")
                
                r2 = requests.get(f'http://localhost:8080/api/products/{ruixin_unit["id"]}')
                if r2.status_code == 200:
                    data2 = r2.json()
                    print(f"产品数量: {data2['count']}")
                    
                    # 检查所有产品，寻找异常格式
                    found_issues = False
                    for i, product in enumerate(data2['products']):
                        name = product.get('name', '')
                        model = product.get('model_number', '')
                        
                        # 检查是否有异常格式
                        if any(keyword in name for keyword in ['桶', 'KG', ',', '规格', '10', '28', '180']):
                            found_issues = True
                            print(f"⚠️ 问题产品 #{i+1}: {model}")
                            print(f"   名称: {repr(name)}")
                            print(f"   长度: {len(name)}")
                    
                    if not found_issues:
                        print("✅ 所有产品格式正常")
                else:
                    print(f"❌ API失败: {r2.status_code}")
        
    except Exception as e:
        print(f"❌ 专门测试失败: {e}")

if __name__ == "__main__":
    test_with_no_cache()
    test_specific_ruixin()
