#!/usr/bin/env python3
# 测试特定型号识别

import requests
import json

def test_specific_model():
    """测试特定型号识别"""
    print("=== 测试特定型号识别 ===")
    
    base_url = "http://localhost:5000"
    
    # 测试不同的输入格式
    test_cases = [
        "博旺，pu哑光米白色漆17#2桶规格25",  # 明确包含17#
        "博旺，17#pu哑光米白色漆2桶规格25",  # 编号在前
        "博旺，pu哑光米白色漆2桶17#规格25",   # 编号在规格后面
        "博旺，pu哑光米白色漆2桶，17#规格25", # 编号独立
        "博旺2桶17#pu哑光米白色漆规格25"      # 简化格式
    ]
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: '{test_text}'")
        print("-" * 60)
        
        try:
            response = requests.post(
                f"{base_url}/api/shipment/parse",
                json={"order_text": test_text, "number_mode": True},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    data = result.get("data", {})
                    products = data.get("products", [])
                    print(f"✅ 解析成功，匹配到 {len(products)} 个产品:")
                    for j, product in enumerate(products, 1):
                        print(f"  产品 {j}:")
                        print(f"    名称: {product.get('name', 'N/A')}")
                        print(f"    型号: {product.get('model_number', 'N/A')}")
                        print(f"    价格: {product.get('unit_price', 'N/A')}")
                        print(f"    数量: {product.get('quantity_tins', 0)}桶")
                else:
                    print(f"❌ 解析失败: {result.get('message', 'Unknown error')}")
            else:
                print(f"❌ API请求失败: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 测试异常: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_specific_model()