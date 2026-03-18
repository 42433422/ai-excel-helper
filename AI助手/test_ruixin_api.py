#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试蕊芯客户API
"""

import urllib.request
import json

def test_ruixin_api():
    try:
        with urllib.request.urlopen('http://localhost:8080/api/products/1') as response:
            data = json.loads(response.read().decode())
            
            print('=== 蕊芯客户API测试结果 ===')
            print(f'API状态: {"成功" if data["success"] else "失败"}')
            print(f'客户名称: {data["customer"]["unit_name"]}')
            print(f'产品数量: {data["count"]}')
            
            if data['products']:
                print(f'\n前5个产品:')
                for i, product in enumerate(data['products'][:5], 1):
                    print(f'{i}. {product["name"]} ({product["model_number"]}) - ¥{product["price"]}')
            else:
                print('没有找到产品数据')
                
    except Exception as e:
        print(f'测试失败: {e}')

if __name__ == "__main__":
    test_ruixin_api()