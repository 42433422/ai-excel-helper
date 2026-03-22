# -*- coding: utf-8 -*-
"""
测试模板列表 API
"""

import requests
import sys

# 测试 API
url = "http://localhost:5000/api/templates/list"

print(f"测试 API: {url}")
print("-" * 80)

try:
    response = requests.get(url, timeout=5)
    print(f"状态码：{response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ API 调用成功!")
        print(f"  success: {data.get('success')}")
        templates = data.get('templates', [])
        print(f"  模板数量：{len(templates)}")
        
        if templates:
            print(f"\n  模板列表:")
            for i, tpl in enumerate(templates[:5], 1):
                print(f"    {i}. {tpl.get('name', 'Unknown')} ({tpl.get('category', 'N/A')})")
    else:
        print(f"✗ API 返回错误状态码：{response.status_code}")
        print(f"  响应内容：{response.text[:200]}")
        
except requests.exceptions.ConnectionError:
    print("✗ 无法连接到服务器，请确保服务正在运行")
    sys.exit(1)
except requests.exceptions.Timeout:
    print("✗ 请求超时")
    sys.exit(1)
except Exception as e:
    print(f"✗ 测试失败：{e}")
    sys.exit(1)

print("\n" + "=" * 80)
print("测试完成!")
