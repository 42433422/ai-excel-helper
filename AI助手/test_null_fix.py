#!/usr/bin/env python3
# 测试修复后的发货单生成功能

import requests
import json

def test_null_fix():
    """测试修复后的发货单生成功能"""
    print("=== 测试修复后的发货单生成功能 ===")
    
    base_url = "http://localhost:5000"
    
    # 测试不同情况，特别关注可能导致NoneType错误的情况
    test_cases = [
        {
            "name": "正常情况-蕊芯家私1",
            "data": {
                "order_text": "蕊芯家私1，PE封固底漆6824A2桶规格25",
                "template_name": "尹玉华1.xlsx",
                "custom_mode": False,
                "number_mode": True
            }
        },
        {
            "name": "正常情况-博旺家私",
            "data": {
                "order_text": "博旺，pu哑光米白色漆17#2桶规格25",
                "template_name": "尹玉华1.xlsx",
                "custom_mode": False,
                "number_mode": True
            }
        },
        {
            "name": "没有购买单位",
            "data": {
                "order_text": "PE封固底漆6824A2桶规格25",
                "template_name": "尹玉华1.xlsx",
                "custom_mode": False,
                "number_mode": True
            }
        },
        {
            "name": "没有编号模式",
            "data": {
                "order_text": "蕊芯家私1，PE封固底漆2桶规格25",
                "template_name": "尹玉华1.xlsx",
                "custom_mode": False,
                "number_mode": False
            }
        },
        {
            "name": "多产品测试",
            "data": {
                "order_text": "蕊芯家私1，PE封固底漆6824A1桶，PE白底漆稀释剂9806A1桶规格25",
                "template_name": "尹玉华1.xlsx",
                "custom_mode": False,
                "number_mode": True
            }
        }
    ]
    
    success_count = 0
    total_count = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test_case['name']}")
        print("-" * 60)
        print(f"输入: {test_case['data']['order_text']}")
        
        try:
            response = requests.post(
                f"{base_url}/api/generate",
                json=test_case['data'],
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            print(f"响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    success_count += 1
                    document = result.get("document", {})
                    products = document.get("products", [])
                    
                    print(f"✅ 发货单生成成功")
                    print(f"  匹配产品数: {len(products)}")
                    
                    # 显示第一个产品的详细信息
                    if products:
                        first_product = products[0]
                        print(f"  第一个产品: {first_product.get('name', 'N/A')} ({first_product.get('model_number', 'N/A')})")
                    
                    # 显示购买单位信息
                    purchase_unit = result.get("purchase_unit")
                    if purchase_unit:
                        print(f"  购买单位: {purchase_unit.get('name', 'N/A')}")
                    else:
                        print(f"  购买单位: 未指定单位")
                else:
                    print(f"❌ 发货单生成失败: {result.get('message', 'Unknown error')}")
            else:
                print(f"❌ API请求失败: {response.status_code}")
                try:
                    error_text = response.text
                    print(f"错误详情: {error_text}")
                except:
                    print("无法获取错误详情")
                    
        except Exception as e:
            print(f"❌ 测试异常: {e}")
    
    print(f"\n=== 测试总结 ===")
    print(f"成功: {success_count}/{total_count}")
    print(f"失败: {total_count - success_count}/{total_count}")
    
    if success_count == total_count:
        print("🎉 所有测试用例通过！NoneType错误已修复！")
    else:
        print("❌ 仍有测试用例失败")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_null_fix()