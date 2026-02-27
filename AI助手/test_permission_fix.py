#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试权限错误修复
"""

import requests
import json

def test_excel_sync():
    """测试Excel同步功能"""
    print("=== 测试Excel同步权限修复 ===")
    
    # 测试订单
    test_order = '七彩乐园PE白底10桶规格28，PE白底稀释剂180kg1桶，Pu哑光白面漆5桶规格20'
    
    # API端点
    url = 'http://localhost:5000/api/generate'
    
    # 请求数据
    data = {
        'order_text': test_order,
        'template_name': '尹玉华1.xlsx',
        'custom_mode': False,
        'number_mode': False,
        'excel_sync': True
    }
    
    print(f"测试订单: {test_order}")
    print(f"请求URL: {url}")
    
    try:
        # 发送请求
        response = requests.post(url, json=data, timeout=30)
        response.encoding = 'utf-8'
        
        # 解析响应
        result = response.json()
        
        print(f"\n响应状态码: {response.status_code}")
        print(f"解析结果: {'成功' if result.get('success', False) else '失败'}")
        
        if result.get('success', False):
            print(f"产品数量: {len(result.get('parsed_data', {}).get('products', []))}")
            print("产品列表:")
            for p in result.get('parsed_data', {}).get('products', []):
                print(f"- {p.get('name', '')} {p.get('quantity_tins', 0)}桶")
            
            if 'excel_sync' in result:
                print(f"Excel同步结果: {result['excel_sync'].get('success', False)}")
                if result['excel_sync'].get('success', False):
                    print("✅ Excel同步成功！")
                else:
                    print("❌ Excel同步失败！")
        else:
            print(f"失败原因: {result.get('message', '未知错误')}")
            
    except Exception as e:
        print(f"请求失败: {e}")

if __name__ == '__main__':
    test_excel_sync()
