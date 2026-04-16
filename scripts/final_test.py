import requests
import time

def final_test():
    """最终测试修复结果"""
    
    print("🎯 最终测试修复结果")
    print("=" * 60)
    
    base_url = "http://127.0.0.1:8000"
    
    # 等待后端完全启动
    print("⏳ 等待后端服务完全启动...")
    time.sleep(5)
    
    # 测试客户列表API
    print("\n📋 测试客户列表API")
    
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
                print("🎉 SQLAlchemy配置修复成功！")
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

def check_frontend_instructions():
    """提供前端验证指导"""
    
    print("\n🔍 前端验证指导")
    print("=" * 60)
    
    print("💡 前端应该显示:")
    print("  - 客户总数: 5")
    print("  - 客户列表: 半岛家具、半岛风情、测试单位1-3")
    print("\n🎯 请刷新前端页面验证结果")
    print("   如果前端仍然显示错误数据，请检查:")
    print("   1. 前端是否有缓存 (Ctrl+F5 强制刷新)")
    print("   2. 前端是否调用了正确的API")
    print("   3. 浏览器开发者工具查看网络请求")

if __name__ == "__main__":
    # 最终测试
    success = final_test()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ SQLAlchemy配置修复完成！")
        print("💡 后端现在使用正确的数据库和模型")
        print("📊 返回正确的购买单位数据")
        
        # 前端指导
        check_frontend_instructions()
        
        print("\n🎉 所有修复工作已完成！")
        print("   请刷新前端页面查看结果")
    else:
        print("\n❌ 修复验证失败")
        print("💡 需要进一步排查问题")