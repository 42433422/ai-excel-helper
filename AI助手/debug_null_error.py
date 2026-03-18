#!/usr/bin/env python3
# 调试发货单生成中的NoneType错误

import requests
import json

def debug_null_error():
    """调试发货单生成中的NoneType错误"""
    print("=== 调试发货单生成中的NoneType错误 ===")
    
    base_url = "http://localhost:5000"
    
    # 测试不同情况
    test_cases = [
        {
            "name": "正常输入",
            "data": {
                "order_text": "蕊芯家私1，PE封固底漆6824A2桶规格25",
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
            "name": "没有型号",
            "data": {
                "order_text": "蕊芯家私1，PE封固底漆2桶规格25",
                "template_name": "尹玉华1.xlsx",
                "custom_mode": False,
                "number_mode": False
            }
        },
        {
            "name": "空白输入",
            "data": {
                "order_text": "",
                "template_name": "尹玉华1.xlsx",
                "custom_mode": False,
                "number_mode": False
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test_case['name']}")
        print("-" * 50)
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
                    print("✅ 发货单生成成功")
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
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    debug_null_error()