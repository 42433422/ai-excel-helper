#!/usr/bin/env python3
# 测试API修复后的前端功能

import requests
import json

def test_api_fix():
    """测试API修复后的前端功能"""
    print("=== 测试API修复后的前端功能 ===")
    
    base_url = "http://localhost:5000"
    
    # 测试数据
    test_data = {
        "order_text": "蕊芯一桶，24-4-8规格25",
        "number_mode": True
    }
    
    try:
        # 测试 /api/shipment/parse 端点
        print(f"测试API端点: {base_url}/api/shipment/parse")
        print(f"请求数据: {test_data}")
        
        response = requests.post(
            f"{base_url}/api/shipment/parse",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容:")
        
        try:
            result = response.json()
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            if result.get("success"):
                print("\n✅ API调用成功")
                data = result.get("data", {})
                products = data.get("products", [])
                
                if products:
                    print(f"解析到 {len(products)} 个产品:")
                    for i, product in enumerate(products, 1):
                        print(f"  产品 {i}: {product.get('name', 'N/A')} ({product.get('model_number', 'N/A')}) - {product.get('quantity_tins', 0)}桶")
                else:
                    print("❌ 没有解析到产品")
            else:
                print(f"❌ API调用失败: {result.get('message', 'Unknown error')}")
                
        except json.JSONDecodeError:
            print(f"❌ JSON解析失败，原始响应: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_api_fix()