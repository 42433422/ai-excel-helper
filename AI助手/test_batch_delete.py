#!/usr/bin/env python3
# 测试批量删除API是否存在

import requests

def test_batch_delete_api():
    """测试批量删除API是否存在"""
    print("=== 测试批量删除API是否存在 ===")
    
    # 测试批量删除API
    try:
        response = requests.post(
            'http://localhost:5000/api/product_names/batch_delete',
            json={
                "name_ids": [1, 2, 3]  # 测试ID
            },
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"批量删除API状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"响应: {result}")
        elif response.status_code == 404:
            print("❌ 批量删除API不存在 (404)")
        elif response.status_code == 405:
            print("❌ 批量删除API不支持POST方法 (405)")
        else:
            print(f"❌ 批量删除API错误: {response.status_code}")
            print(f"错误内容: {response.text}")
            
    except Exception as e:
        print(f"❌ 批量删除API连接错误: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_batch_delete_api()