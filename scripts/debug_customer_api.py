import requests

def debug_customer_api():
    """调试客户 API"""
    
    print("🔍 调试客户 API")
    print("=" * 60)
    
    base_url = "http://127.0.0.1:8000"
    
    # 测试客户列表 API
    print("\n📋 测试客户列表 API")
    
    response = requests.get(f"{base_url}/api/customers", timeout=10)
    
    print(f"状态码：{response.status_code}")
    print(f"响应数据：{response.json()}")
    
    # 测试单个客户 API
    print("\n📋 测试单个客户 API (ID: 1)")
    
    response = requests.get(f"{base_url}/api/customers/1", timeout=10)
    
    print(f"状态码：{response.status_code}")
    print(f"响应数据：{response.json()}")

if __name__ == "__main__":
    debug_customer_api()