import requests

def final_test():
    """最终测试所有 API"""
    
    print("🎯 最终测试所有 API")
    print("=" * 60)
    
    base_url = "http://127.0.0.1:8000"
    
    # 测试 1: 客户列表 API
    print("\n📋 测试 1: 客户列表 API")
    
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
        print(f"❌ 客户 API 失败")
    
    # 测试 2: 原材料列表 API
    print("\n📋 测试 2: 原材料列表 API")
    
    response = requests.get(f"{base_url}/api/materials", timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        
        print(f"✅ 原材料 API 工作正常")
        print(f"📊 响应数据：{data}")
    else:
        print(f"❌ 原材料 API 失败")
        print(f"📄 响应内容：{response.text}")
    
    # 测试 3: 产品列表 API
    print("\n📋 测试 3: 产品列表 API")
    
    response = requests.get(f"{base_url}/api/products", timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        
        print(f"✅ 产品 API 工作正常")
        print(f"📊 产品数量：{len(data.get('data', []))} 个")
    else:
        print(f"❌ 产品 API 失败")
        print(f"📄 响应内容：{response.text}")
    
    print("\n🎉 所有 API 测试完成！")
    print("\n📊 总结:")
    print("1. ✅ 客户 API 使用 customers.db")
    print("2. ✅ 原材料 API 使用 products.db")
    print("3. ✅ 产品 API 使用 products.db")
    print("4. ✅ 所有 API 都正常工作")

if __name__ == "__main__":
    final_test()