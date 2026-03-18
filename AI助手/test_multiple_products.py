#!/usr/bin/env python3
# 测试多个产品的编号模式

import requests
import json

def test_multiple_products():
    """测试多个产品的编号模式"""
    print("=== 测试多个产品的编号模式 ===")
    
    base_url = "http://localhost:5000"
    
    # 测试不同产品编号
    test_cases = [
        {
            "name": "PE封固底漆",
            "data": {
                "order_text": "蕊芯一桶6824A规格25",
                "number_mode": True
            }
        },
        {
            "name": "PE稀释剂",
            "data": {
                "order_text": "蕊芯一桶9806A规格25",
                "number_mode": True
            }
        },
        {
            "name": "多产品混合",
            "data": {
                "order_text": "蕊芯一桶6824A，一桶9806A，一桶24-4-8规格25",
                "number_mode": True
            }
        },
        {
            "name": "名称+编号组合",
            "data": {
                "order_text": "蕊芯一桶PE封固底漆6824A规格25",
                "number_mode": True
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test_case['name']}")
        print("-" * 50)
        print(f"输入: {test_case['data']['order_text']}")
        
        try:
            response = requests.post(
                f"{base_url}/api/shipment/parse",
                json=test_case['data'],
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    products = result.get("data", {}).get("products", [])
                    print(f"✅ 解析成功，匹配到 {len(products)} 个产品:")
                    for j, product in enumerate(products, 1):
                        print(f"  产品 {j}: {product.get('name', 'N/A')} ({product.get('model_number', 'N/A')}) - {product.get('quantity_tins', 0)}桶")
                else:
                    print(f"❌ 解析失败: {result.get('message', 'Unknown error')}")
            else:
                print(f"❌ API请求失败: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 测试异常: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_multiple_products()