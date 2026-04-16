import sqlite3

def verify_db_copy():
    """验证数据库复制结果"""
    
    print("🔍 验证数据库复制结果")
    print("=" * 60)
    
    # 检查目标数据库
    target_db = "e:/FHD/xcagi/customers.db"
    
    try:
        conn = sqlite3.connect(target_db)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='purchase_units'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("❌ purchase_units表不存在")
            conn.close()
            return False
        
        # 检查活跃购买单位数量
        cursor.execute("SELECT COUNT(*) FROM purchase_units WHERE is_active = 1")
        count = cursor.fetchone()[0]
        
        # 获取购买单位列表
        cursor.execute("SELECT id, unit_name FROM purchase_units WHERE is_active = 1 ORDER BY unit_name")
        units = cursor.fetchall()
        
        print(f"✅ 数据库复制成功")
        print(f"📊 活跃购买单位: {count} 个")
        print("🏷️ 购买单位列表:")
        for unit in units:
            print(f"  - ID: {unit[0]}, 名称: {unit[1]}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 验证数据库失败: {e}")
        return False

def check_backend_api():
    """检查后端API"""
    
    print("\n🔍 检查后端API")
    print("=" * 60)
    
    import requests
    
    base_url = "http://127.0.0.1:8000"
    
    try:
        response = requests.get(f"{base_url}/api/customers", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            customers = data.get("data", [])
            
            print(f"📊 /api/customers 返回 {len(customers)} 个客户")
            
            if customers:
                print("📋 客户列表:")
                for customer in customers:
                    print(f"  - ID: {customer['id']}, 名称: {customer['customer_name']}")
            
            # 检查是否返回了正确的数据
            expected_customers = ["半岛风情", "半岛家具", "测试单位1", "测试单位2", "测试单位3"]
            actual_customers = [c['customer_name'] for c in customers]
            
            if set(expected_customers).issubset(set(actual_customers)):
                print("✅ 后端API现在返回正确的购买单位数据！")
                return True
            else:
                print("❌ 后端API仍然返回错误的数据")
                return False
                
        else:
            print(f"❌ API请求失败，状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 检查后端API失败: {e}")
        return False

if __name__ == "__main__":
    # 验证数据库复制
    db_ok = verify_db_copy()
    
    if db_ok:
        print("\n✅ 数据库复制验证完成")
        print("💡 现在需要重启后端服务")
        
        # 检查后端API
        api_ok = check_backend_api()
        
        if not api_ok:
            print("\n🔧 需要重启后端服务")
            print("   请运行: cd e:/FHD/xcagi && python run.py")
    else:
        print("\n❌ 数据库复制验证失败")