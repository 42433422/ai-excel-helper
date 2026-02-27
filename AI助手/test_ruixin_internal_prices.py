#!/usr/bin/env python3
# 测试蕊芯家私1内部价格在发货单中的实际应用

import requests
import json

def test_ruixin_internal_prices():
    """测试蕊芯家私1内部价格在发货单中的实际应用"""
    print("=== 测试蕊芯家私1内部价格在发货单中的实际应用 ===")
    
    base_url = "http://localhost:5000"
    
    # 测试蕊芯家私1的产品价格
    test_cases = [
        {
            "name": "PE封固底漆6824A",
            "input": "蕊芯家私1，PE封固底漆6824A2桶规格25",
            "expected_price": 13.0,  # 内部价
            "general_price": 14.5     # 通用价
        },
        {
            "name": "PU哑光银珠漆5020#",
            "input": "蕊芯家私1，PU哑光银珠漆5020#2桶规格25",
            "expected_price": 24.0,  # 内部价
            "general_price": 28.0     # 通用价
        },
        {
            "name": "PE白底漆9806",
            "input": "蕊芯家私1，PE白底漆9806A2桶规格25",
            "expected_price": 7.0,   # 内部价
            "general_price": 7.5     # 通用价
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test_case['name']}")
        print("-" * 60)
        print(f"输入: {test_case['input']}")
        print(f"期望价格: {test_case['expected_price']}元 (内部价)")
        print(f"对比价格: {test_case['general_price']}元 (通用价)")
        
        try:
            response = requests.post(
                f"{base_url}/api/generate",
                json={
                    "order_text": test_case['input'],
                    "template_name": "尹玉华1.xlsx",
                    "custom_mode": False,
                    "number_mode": True
                },
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    document = result.get("document", {})
                    products = document.get("products", [])
                    
                    if products:
                        product = products[0]
                        actual_price = product.get("unit_price", 0)
                        
                        print(f"实际价格: {actual_price}元")
                        
                        if actual_price == test_case['expected_price']:
                            print("✅ 正确使用内部价")
                        elif actual_price == test_case['general_price']:
                            print("❌ 错误使用通用价")
                        else:
                            print(f"❌ 未知价格: {actual_price}元")
                        
                        # 显示产品详情
                        print(f"产品详情:")
                        print(f"  名称: {product.get('name', 'N/A')}")
                        print(f"  型号: {product.get('model_number', 'N/A')}")
                        print(f"  数量: {product.get('quantity_tins', 0)}桶")
                        print(f"  单价: {product.get('unit_price', 'N/A')}元")
                        print(f"  金额: {product.get('amount', 'N/A')}元")
                    else:
                        print("❌ 未找到产品")
                else:
                    print(f"❌ 发货单生成失败: {result.get('message', 'Unknown error')}")
            else:
                print(f"❌ API请求失败: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 测试异常: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_ruixin_internal_prices()