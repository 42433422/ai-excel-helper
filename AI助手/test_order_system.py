#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试订单管理系统
"""

import requests
import json
import time

def test_order_system():
    """测试订单管理系统"""
    base_url = 'http://localhost:5000'
    
    print("=== 测试订单管理系统 ===")
    print(f"API基础URL: {base_url}")
    print()
    
    # 1. 测试订单生成和保存
    print("1. 测试订单生成和保存...")
    
    test_order = '七彩乐园PE白底10桶规格28，PE白底稀释剂180kg1桶，Pu哑光白面漆5桶规格20'
    
    generate_data = {
        'order_text': test_order,
        'template_name': '尹玉华1.xlsx',
        'custom_mode': False,
        'number_mode': False,
        'excel_sync': True
    }
    
    try:
        response = requests.post(f'{base_url}/api/generate', json=generate_data, timeout=30)
        response.encoding = 'utf-8'
        generate_result = response.json()
        
        print(f"   响应状态码: {response.status_code}")
        print(f"   生成结果: {'成功' if generate_result.get('success', False) else '失败'}")
        
        if generate_result.get('success', False):
            order_number = generate_result.get('document', {}).get('order_number', '')
            order_id = generate_result.get('order_id')
            
            print(f"   订单编号: {order_number}")
            print(f"   订单ID: {order_id}")
            print(f"   产品数量: {len(generate_result.get('parsed_data', {}).get('products', []))}")
            print("   ✅ 订单生成和保存成功！")
            
            # 2. 测试订单搜索
            print("\n2. 测试订单搜索...")
            
            # 等待一秒，确保数据已保存
            time.sleep(1)
            
            # 按订单编号搜索
            search_response = requests.get(f'{base_url}/api/orders/search', params={'q': order_number}, timeout=10)
            search_result = search_response.json()
            
            print(f"   响应状态码: {search_response.status_code}")
            print(f"   搜索结果数量: {len(search_result.get('data', []))}")
            
            if search_result.get('data'):
                print(f"   找到订单: {search_result.get('data', [])[0].get('order_number')}")
                print("   ✅ 订单搜索成功！")
            else:
                print("   ❌ 订单搜索失败，未找到订单")
            
            # 3. 测试订单详情查询
            print("\n3. 测试订单详情查询...")
            
            detail_response = requests.get(f'{base_url}/api/orders/{order_number}', timeout=10)
            detail_result = detail_response.json()
            
            print(f"   响应状态码: {detail_response.status_code}")
            print(f"   查询结果: {'成功' if detail_result.get('success', False) else '失败'}")
            
            if detail_result.get('success', False):
                order_data = detail_result.get('data', {})
                print(f"   订单编号: {order_data.get('order_number')}")
                print(f"   购买单位: {order_data.get('purchase_unit')}")
                print(f"   产品数量: {len(order_data.get('products', []))}")
                print(f"   总金额: {order_data.get('total_amount')}")
                print("   ✅ 订单详情查询成功！")
            else:
                print(f"   ❌ 订单详情查询失败: {detail_result.get('message')}")
            
            # 4. 测试订单列表
            print("\n4. 测试订单列表...")
            
            list_response = requests.get(f'{base_url}/api/orders', params={'limit': 10}, timeout=10)
            list_result = list_response.json()
            
            print(f"   响应状态码: {list_response.status_code}")
            print(f"   订单列表数量: {len(list_result.get('data', []))}")
            
            if list_result.get('data'):
                print(f"   最新订单编号: {list_result.get('data', [])[0].get('order_number')}")
                print("   ✅ 订单列表查询成功！")
            else:
                print("   ❌ 订单列表查询失败")
            
        else:
            print(f"   ❌ 订单生成失败: {generate_result.get('message')}")
            
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == '__main__':
    test_order_system()
