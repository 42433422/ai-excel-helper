import requests
import json

def test_delete_function():
    """测试删除功能"""
    
    print("🔍 测试删除功能")
    print("=" * 60)
    
    base_url = "http://127.0.0.1:8000"
    
    # 1. 先获取当前客户列表
    print("📋 1. 获取当前客户列表")
    
    try:
        response = requests.get(f"{base_url}/api/customers", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            customers = data.get("data", [])
            
            print(f"✅ 当前客户数量: {len(customers)} 个")
            print("📋 客户列表:")
            for customer in customers:
                print(f"  - ID: {customer['id']}, 名称: {customer['customer_name']}")
            
            if len(customers) == 0:
                print("❌ 没有客户数据，无法测试删除功能")
                return
                
            # 选择第一个客户进行删除测试
            test_customer = customers[0]
            customer_id = test_customer['id']
            customer_name = test_customer['customer_name']
            
            print(f"\n🔧 2. 测试删除客户: {customer_name} (ID: {customer_id})")
            
            # 2. 测试删除API
            delete_url = f"{base_url}/api/customers/{customer_id}"
            print(f"  删除URL: {delete_url}")
            
            delete_response = requests.delete(delete_url, timeout=10)
            
            if delete_response.status_code == 200:
                delete_data = delete_response.json()
                print(f"✅ 删除API响应: {json.dumps(delete_data, ensure_ascii=False)}")
                
                if delete_data.get("success"):
                    print("✅ 删除操作成功")
                else:
                    print("❌ 删除操作失败")
                    
            else:
                print(f"❌ 删除API请求失败，状态码: {delete_response.status_code}")
                print(f"📄 响应内容: {delete_response.text}")
            
            # 3. 再次获取客户列表验证删除结果
            print(f"\n🔍 3. 验证删除结果")
            
            response2 = requests.get(f"{base_url}/api/customers", timeout=10)
            
            if response2.status_code == 200:
                data2 = response2.json()
                customers2 = data2.get("data", [])
                
                print(f"✅ 删除后客户数量: {len(customers2)} 个")
                print("📋 删除后客户列表:")
                for customer in customers2:
                    print(f"  - ID: {customer['id']}, 名称: {customer['customer_name']}")
                
                # 检查被删除的客户是否还在列表中
                deleted_still_exists = any(c['id'] == customer_id for c in customers2)
                
                if deleted_still_exists:
                    print("❌ 删除失败：客户仍然存在")
                else:
                    print("✅ 删除成功：客户已从列表中移除")
                    
            else:
                print(f"❌ 验证删除结果失败，状态码: {response2.status_code}")
                
        else:
            print(f"❌ 获取客户列表失败，状态码: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 测试删除功能失败: {e}")

def check_database_after_delete():
    """检查数据库删除后的状态"""
    
    print("\n🔍 检查数据库状态")
    print("=" * 60)
    
    import sqlite3
    
    db_path = "e:/FHD/xcagi/customers.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查purchase_units表
        cursor.execute("SELECT COUNT(*) FROM purchase_units WHERE is_active = 1")
        active_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM purchase_units WHERE is_active = 0")
        inactive_count = cursor.fetchone()[0]
        
        print(f"📊 数据库状态:")
        print(f"  活跃客户: {active_count} 个")
        print(f"  非活跃客户: {inactive_count} 个")
        print(f"  总客户数: {active_count + inactive_count} 个")
        
        # 检查删除操作是软删除还是硬删除
        if inactive_count > 0:
            print("💡 删除操作可能是软删除（设置is_active=0）")
        else:
            print("💡 删除操作可能是硬删除（直接从数据库删除）")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 检查数据库失败: {e}")

def check_delete_implementation():
    """检查删除功能的实现方式"""
    
    print("\n🔍 检查删除功能实现")
    print("=" * 60)
    
    # 检查customer_import_service.py中的删除实现
    service_file = "e:/FHD/xcagi/app/services/customer_import_service.py"
    
    try:
        with open(service_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 查找删除相关的代码
            if "db.delete(customer)" in content:
                print("✅ 删除实现: 硬删除（直接从数据库删除记录）")
            elif "is_active = 0" in content or "is_active=0" in content:
                print("✅ 删除实现: 软删除（设置is_active=0）")
            else:
                print("❓ 删除实现: 未知方式")
                
            # 检查是否有软删除逻辑
            if "软删除" in content:
                print("💡 代码中包含软删除注释")
            
    except Exception as e:
        print(f"❌ 检查删除实现失败: {e}")

if __name__ == "__main__":
    # 测试删除功能
    test_delete_function()
    
    # 检查数据库状态
    check_database_after_delete()
    
    # 检查删除实现
    check_delete_implementation()
    
    print("\n🎯 问题分析:")
    print("1. 如果删除后客户数量减少，但数据库记录还在 → 软删除")
    print("2. 如果删除后数据库记录消失 → 硬删除")
    print("3. 如果删除后前端不刷新 → 前端缓存问题")
    print("4. 如果删除后数据丢失 → 删除逻辑有问题")