#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests

def test_order_api():
    try:
        # 测试获取订单列表
        response = requests.get('http://localhost:5000/api/orders?limit=10&page=1')
        print('🎯 测试订单查询API:')
        print(f'Status: {response.status_code}')
        data = response.json()
        print(f'订单总数: {len(data.get("data", []))}')
        
        if data.get('data'):
            print('📋 前3个订单:')
            for order in data['data'][:3]:
                print(f'  - 订单号: {order.get("order_number")}, 购买单位: {order.get("purchase_unit")}, 金额: {order.get("total_amount")}')
        
        # 测试购买单位列表
        response = requests.get('http://localhost:5000/api/orders/purchase-units')
        print('\n🏭 测试购买单位API:')
        print(f'Status: {response.status_code}')
        data = response.json()
        print(f'购买单位列表: {data.get("data", [])}')
        
    except Exception as e:
        print(f'API测试失败: {e}')

if __name__ == '__main__':
    test_order_api()