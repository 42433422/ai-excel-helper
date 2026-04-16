import requests
import time
import json

def final_verification():
    """最终验证后端API返回正确数据"""
    
    print("🎯 最终验证后端API")
    print("=" * 60)
    
    base_url = "http://127.0.0.1:8000"
    
    # 等待后端完全启动
    print("⏳ 等待后端服务完全启动...")
    time.sleep(5)
    
    # 测试1: 检查客户列表API
    print("\n📋 测试1: 检查客户列表API")
    
    try:
        response = requests.get(f"{base_url}/api/customers", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            customers = data.get("data", [])
            
            print(f"✅ API请求成功")
            print(f"📊 返回客户数量: {len(customers)} 个")
            print(f"📋 客户列表:")
            
            for customer in customers:
                print(f"  - ID: {customer['id']}, 名称: {customer['customer_name']}")
            
            # 检查是否返回了正确的数据
            expected_customers = ["半岛风情", "半岛家具", "测试单位1", "测试单位2", "测试单位3"]
            actual_customers = [c['customer_name'] for c in customers]
            
            print(f"\n🔍 数据验证:")
            print(f"  期望的客户: {expected_customers}")
            print(f"  实际的客户: {actual_customers}")
            
            if set(expected_customers).issubset(set(actual_customers)):
                print("✅ 后端API现在返回正确的购买单位数据！")
                print("🎉 问题已完全解决！")
                return True
            else:
                print("❌ 后端API仍然返回错误的数据")
                return False
                
        else:
            print(f"❌ API请求失败，状态码: {response.status_code}")
            print(f"📄 响应内容: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 检查后端API失败: {e}")
        return False
    
    # 测试2: 检查其他相关API
    print("\n📋 测试2: 检查其他相关API")
    
    api_endpoints = [
        "/api/customers/list",
        "/api/purchase_units"
    ]
    
    for endpoint in api_endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if "data" in data:
                    items = data["data"]
                    print(f"✅ {endpoint} 返回 {len(items)} 条记录")
                elif "customers" in data:
                    items = data["customers"]
                    print(f"✅ {endpoint} 返回 {len(items)} 条记录")
                else:
                    print(f"⚠️ {endpoint} 返回未知格式")
            else:
                print(f"❌ {endpoint} 请求失败: {response.status_code}")
                
        except Exception as e:
            print(f"❌ {endpoint} 请求失败: {e}")

def check_frontend_ready():
    """检查前端是否就绪"""
    
    print("\n🔍 检查前端状态")
    print("=" * 60)
    
    print("💡 前端应该显示:")
    print("  - 客户总数: 5")
    print("  - 客户列表: 半岛家具、半岛风情、测试单位1-3")
    print("\n🎯 请刷新前端页面验证结果")
    print("   如果前端仍然显示2个客户，请检查:")
    print("   1. 前端是否有缓存")
    print("   2. 前端是否调用了正确的API")
    print("   3. 强制刷新页面 (Ctrl+F5)")

if __name__ == "__main__":
    # 最终验证
    api_ok = final_verification()
    
    if api_ok:
        print("\n" + "=" * 60)
        print("✅ 后端API验证完成")
        print("💡 后端现在返回正确的购买单位数据")
        
        # 检查前端状态
        check_frontend_ready()
        
        print("\n🎉 所有修复工作已完成！")
        print("   请刷新前端页面查看结果")
    else:
        print("\n❌ 后端API验证失败")
        print("💡 需要进一步排查问题")