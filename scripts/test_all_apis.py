import requests
import json

def test_all_apis():
    """测试所有 API"""
    
    print("🔍 测试所有 API")
    print("=" * 60)
    
    base_url = "http://127.0.0.1:8000"
    
    # 测试 1: 客户列表 API
    print("\n📋 测试 1: 客户列表 API")
    
    try:
        response = requests.get(f"{base_url}/api/customers", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            customers = data.get("data", [])
            
            print(f"✅ 客户 API 工作正常")
            print(f"📊 客户数量：{len(customers)} 个")
            print("📋 客户列表:")
            for customer in customers:
                print(f"  - ID: {customer['id']}, 名称：{customer['customer_name']}")
        else:
            print(f"❌ 客户 API 失败，状态码：{response.status_code}")
            
    except Exception as e:
        print(f"❌ 客户 API 异常：{e}")
    
    # 测试 2: 原材料列表 API
    print("\n📋 测试 2: 原材料列表 API")
    
    try:
        response = requests.get(f"{base_url}/api/materials", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            materials = data.get("data", [])
            
            print(f"✅ 原材料 API 工作正常")
            print(f"📊 原材料数量：{len(materials)} 个")
            
            if materials:
                print("📋 原材料列表 (前 5 个):")
                for material in materials[:5]:
                    print(f"  - ID: {material['id']}, 名称：{material['name']}, 编码：{material['material_code']}")
        else:
            print(f"❌ 原材料 API 失败，状态码：{response.status_code}")
            print(f"📄 响应内容：{response.text}")
            
    except Exception as e:
        print(f"❌ 原材料 API 异常：{e}")
    
    # 测试 3: 产品列表 API
    print("\n📋 测试 3: 产品列表 API")
    
    try:
        response = requests.get(f"{base_url}/api/products", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            products = data.get("data", [])
            
            print(f"✅ 产品 API 工作正常")
            print(f"📊 产品数量：{len(products)} 个")
            
            if products:
                print("📋 产品列表 (前 5 个):")
                for product in products[:5]:
                    print(f"  - ID: {product['id']}, 名称：{product['product_name']}")
        else:
            print(f"❌ 产品 API 失败，状态码：{response.status_code}")
            print(f"📄 响应内容：{response.text}")
            
    except Exception as e:
        print(f"❌ 产品 API 异常：{e}")
    
    print("\n🎯 测试总结:")
    print("1. 客户 API: 使用 customers.db")
    print("2. 原材料 API: 使用 products.db")
    print("3. 产品 API: 使用 products.db")
    print("4. 所有 API 都应该正常工作")

if __name__ == "__main__":
    test_all_apis()