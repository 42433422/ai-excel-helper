#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json

def test_system_apis():
    """测试系统API状态"""
    try:
        print('🎯 测试系统API状态...')
        
        # 测试订单查询API
        response = requests.get('http://127.0.0.1:5000/api/orders?limit=3&page=1')
        if response.status_code == 200:
            data = response.json()
            orders_count = len(data.get("data", []))
            print(f'✅ 订单查询API正常: {orders_count} 个订单')
        else:
            print(f'❌ 订单查询API错误: {response.status_code}')
        
        # 测试打印机API
        response = requests.get('http://127.0.0.1:5000/api/printers')
        if response.status_code == 200:
            data = response.json()
            printers = data.get('printers', [])
            print(f'✅ 打印机API正常: {len(printers)} 个打印机')
            if len(printers) >= 2:
                print(f'   - 第一个打印机: {printers[0].get("name", "Unknown")}')
                print(f'   - 第二个打印机: {printers[1].get("name", "Unknown")} ← 用于标签打印')
        else:
            print(f'❌ 打印机API错误: {response.status_code}')
            
        print('\n🎉 系统API测试完成!')
        
    except Exception as e:
        print(f'❌ API测试失败: {e}')

if __name__ == '__main__':
    test_system_apis()