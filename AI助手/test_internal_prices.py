#!/usr/bin/env python3
# 测试内部价在实际生成发货单时是否生效

import requests
import json

def test_internal_prices():
    """测试内部价在实际生成发货单时是否生效"""
    print("=== 测试内部价在实际生成发货单时是否生效 ===")
    
    base_url = "http://localhost:5000"
    
    # 测试数据
    test_cases = [
        {
            "name": "PE封固底漆",
            "data": {
                "order_text": "蕊芯家私1，PE封固底漆6824A2桶规格25",
                "template_name": "尹玉华1.xlsx",
                "custom_mode": False,
                "number_mode": True
            }
        },
        {
            "name": "哑光银珠漆",
            "data": {
                "order_text": "蕊芯家私1，PU哑光银珠漆5020#2桶规格25",
                "template_name": "尹玉华1.xlsx",
                "custom_mode": False,
                "number_mode": True
            }
        },
        {
            "name": "PE白底漆稀释剂",
            "data": {
                "order_text": "蕊芯家私1，PE白底漆稀释剂9806A2桶规格25",
                "template_name": "尹玉华1.xlsx",
                "custom_mode": False,
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
                f"{base_url}/api/generate",
                json=test_case['data'],
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    document = result.get("document", {})
                    products = document.get("products", [])
                    print(f"✅ 发货单生成成功，匹配到 {len(products)} 个产品:")
                    
                    for j, product in enumerate(products, 1):
                        print(f"  产品 {j}:")
                        print(f"    名称: {product.get('name', 'N/A')}")
                        print(f"    型号: {product.get('model_number', 'N/A')}")
                        print(f"    数量: {product.get('quantity_tins', 0)}桶")
                        print(f"    单价: {product.get('unit_price', 'N/A')}元")
                        print(f"    金额: {product.get('total_amount', 'N/A')}元")
                        print(f"    购买单位: {document.get('purchase_unit', {}).get('name', 'N/A')}")
                else:
                    print(f"❌ 发货单生成失败: {result.get('message', 'Unknown error')}")
            else:
                print(f"❌ API请求失败: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 测试异常: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_internal_prices()