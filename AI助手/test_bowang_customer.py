#!/usr/bin/env python3
# 测试博旺客户的产品匹配

import requests
import json

def test_bowang_customer():
    """测试博旺客户的产品匹配"""
    print("=== 测试博旺客户的产品匹配 ===")
    
    base_url = "http://localhost:5000"
    
    # 测试博旺客户的订单
    test_data = {
        "order_text": "博旺，pu哑光米白色漆2桶规格25",
        "number_mode": True
    }
    
    try:
        print(f"测试输入: {test_data['order_text']}")
        print("-" * 50)
        
        # 测试解析功能
        print("1. 测试 /api/shipment/parse 端点:")
        response = requests.post(
            f"{base_url}/api/shipment/parse",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                data = result.get("data", {})
                products = data.get("products", [])
                print(f"✅ 解析成功，匹配到 {len(products)} 个产品:")
                for i, product in enumerate(products, 1):
                    print(f"  产品 {i}:")
                    print(f"    名称: {product.get('name', 'N/A')}")
                    print(f"    型号: {product.get('model_number', 'N/A')}")
                    print(f"    数量: {product.get('quantity_tins', 0)}桶, {product.get('quantity_kg', 0)}公斤")
                    print(f"    购买单位: {data.get('purchase_unit', 'N/A')}")
                print()
            else:
                print(f"❌ 解析失败: {result.get('message', 'Unknown error')}")
        else:
            print(f"❌ API请求失败: {response.status_code}")
        
        # 测试生成发货单
        print("2. 测试生成发货单:")
        generate_data = {
            "order_text": "博旺，pu哑光米白色漆2桶规格25",
            "template_name": "尹玉华1.xlsx",
            "custom_mode": False,
            "number_mode": True
        }
        
        response = requests.post(
            f"{base_url}/api/generate",
            json=generate_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                document = result.get("document", {})
                products = document.get("products", [])
                print(f"✅ 发货单生成成功，匹配到 {len(products)} 个产品:")
                for i, product in enumerate(products, 1):
                    print(f"  产品 {i}:")
                    print(f"    名称: {product.get('name', 'N/A')}")
                    print(f"    型号: {product.get('model_number', 'N/A')}")
                    print(f"    数量: {product.get('quantity_tins', 0)}桶, {product.get('quantity_tins', 0) * product.get('tin_spec', 0)}公斤")
                    print(f"    购买单位: {document.get('purchase_unit', {}).get('name', 'N/A')}")
                print(f"    生成文件: {document.get('filename', 'N/A')}")
            else:
                print(f"❌ 发货单生成失败: {result.get('message', 'Unknown error')}")
        else:
            print(f"❌ 生成API请求失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 测试异常: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_bowang_customer()