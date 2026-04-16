import requests
import json

def frontend_smoke_test():
    """前端冒烟测试 - 检查前端实际调用的API和数据"""
    
    # 后端 API 基础 URL（默认 FastAPI http_app，PORT=8000）
    base_url = "http://127.0.0.1:8000"
    
    print("🔥 前端冒烟测试")
    print("=" * 60)
    
    # 测试1: 检查前端调用的客户列表API
    print("\n📋 测试1: 检查前端调用的客户列表API")
    
    # 前端可能调用的API端点
    api_endpoints = [
        "/api/customers",
        "/api/customers/list", 
        "/api/customers/",
        "/api/purchase_units",
        "/api/units"
    ]
    
    for endpoint in api_endpoints:
        try:
            url = base_url + endpoint
            print(f"\n🔍 测试API: {url}")
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 状态码: {response.status_code}")
                print(f"📊 响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
                
                # 检查数据内容
                if "data" in data:
                    customers = data["data"]
                    print(f"👥 客户数量: {len(customers)}")
                    if customers:
                        print("📋 客户列表:")
                        for i, customer in enumerate(customers[:5]):  # 只显示前5个
                            customer_name = customer.get('customer_name') or customer.get('unit_name') or customer.get('name', '未知')
                            print(f"  {i+1}. {customer_name}")
                elif "customers" in data:
                    customers = data["customers"]
                    print(f"👥 客户数量: {len(customers)}")
                    if customers:
                        print("📋 客户列表:")
                        for i, customer in enumerate(customers[:5]):
                            customer_name = customer.get('customer_name') or customer.get('unit_name') or customer.get('name', '未知')
                            print(f"  {i+1}. {customer_name}")
            else:
                print(f"❌ 状态码: {response.status_code}")
                print(f"📄 响应内容: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 请求失败: {e}")
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
            print(f"📄 原始响应: {response.text}")
    
    # 测试2: 检查后端是否正在运行
    print("\n📋 测试2: 检查后端服务状态")
    
    health_endpoints = ["/", "/health", "/api/health"]
    
    for endpoint in health_endpoints:
        try:
            url = base_url + endpoint
            response = requests.get(url, timeout=5)
            print(f"🔍 {url} - 状态码: {response.status_code}")
        except:
            print(f"🔍 {url} - 连接失败")
    
    # 测试3: 直接检查数据库数据
    print("\n📋 测试3: 直接检查数据库数据")
    
    import sqlite3
    
    # 检查customer数据库
    customer_db = "e:/FHD/424/customers.db"
    try:
        conn = sqlite3.connect(customer_db)
        cursor = conn.cursor()
        
        # 检查purchase_units表
        cursor.execute("SELECT COUNT(*) FROM purchase_units WHERE is_active = 1")
        active_count = cursor.fetchone()[0]
        print(f"📊 customer数据库活跃购买单位: {active_count} 个")
        
        cursor.execute("SELECT id, unit_name FROM purchase_units WHERE is_active = 1 ORDER BY unit_name")
        units = cursor.fetchall()
        
        if units:
            print("🏷️ 数据库中的购买单位:")
            for unit in units:
                print(f"  - ID: {unit[0]}, 名称: {unit[1]}")
        
        conn.close()
    except Exception as e:
        print(f"❌ 检查customer数据库失败: {e}")
    
    # 测试4: 检查前端可能使用的其他数据源
    print("\n📋 测试4: 检查前端可能使用的其他数据源")
    
    # 检查是否有硬编码数据或示例数据
    print("💡 前端可能使用:")
    print("  - 硬编码的示例数据")
    print(" - 本地存储的数据")
    print("  - 模拟数据")
    print("  - 不同的数据库表")
    
    # 测试5: 检查前端JavaScript文件中的API调用
    print("\n📋 测试5: 检查前端JavaScript中的API调用")
    
    # 检查前端JS文件中的API调用模式
    js_files = [
        "e:/FHD/XCAGI/frontend/public/static/js/modules/customers.js",
        "e:/FHD/XCAGI/frontend/src/api/customers.js"
    ]
    
    for js_file in js_files:
        try:
            with open(js_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 查找API调用
                api_patterns = [
                    "fetch.*/api/customers",
                    "api.get.*/api/customers",
                    "axios.get.*/api/customers",
                    "loadCustomers"
                ]
                
                print(f"\n🔍 检查文件: {js_file}")
                for pattern in api_patterns:
                    if pattern in content:
                        print(f"  ✅ 找到API调用模式: {pattern}")
                        
                        # 提取相关代码片段
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if pattern in line:
                                print(f"    行 {i+1}: {line.strip()}")
                                
        except FileNotFoundError:
            print(f"❌ 文件不存在: {js_file}")
        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
    
    print("\n" + "=" * 60)
    print("💡 总结和建议:")
    print("1. 检查后端API是否返回正确的数据")
    print("2. 检查前端是否调用了正确的API端点")
    print("3. 检查是否有缓存或硬编码数据")
    print("4. 检查前端和后端的数据格式是否匹配")

def check_backend_implementation():
    """检查后端实际实现"""
    
    print("\n🔍 检查后端实际实现")
    print("=" * 60)
    
    # 检查后端路由文件
    routes_file = "e:/FHD/xcagi/app/routes/customers.py"
    
    try:
        with open(routes_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 查找路由定义
            import re
            routes = re.findall(r'@customers_bp\.route\("([^"]+)"', content)
            
            print("🏷️ 后端定义的路由:")
            for route in routes:
                print(f"  - {route}")
                
            # 查找get_all_customers函数调用
            if "get_all_customers" in content:
                print("\n🔧 后端使用get_all_customers函数")
                
                # 查找服务调用
                service_patterns = [
                    "get_customer_import_service",
                    "CustomerService",
                    "customer_service"
                ]
                
                for pattern in service_patterns:
                    if pattern in content:
                        print(f"  ✅ 使用服务: {pattern}")
                        
    except Exception as e:
        print(f"❌ 检查后端实现失败: {e}")

if __name__ == "__main__":
    frontend_smoke_test()
    check_backend_implementation()
    
    print("\n🎯 下一步:")
    print("1. 启动后端服务")
    print("2. 运行冒烟测试查看实际API响应")
    print("3. 根据测试结果修复问题")