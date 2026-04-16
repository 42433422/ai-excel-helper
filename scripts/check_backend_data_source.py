import sqlite3
import requests

def check_backend_data_source():
    """检查后端实际使用的数据源"""
    
    print("🔍 检查后端实际使用的数据源")
    print("=" * 60)
    
    # 检查后端可能使用的数据库
    possible_dbs = [
        "e:/FHD/xcagi/app.db",
        "e:/FHD/xcagi/instance/app.db", 
        "e:/FHD/xcagi/data/app.db",
        "e:/FHD/424/customers.db",
        "e:/FHD/98k/AI助手/AI助手/products.db"
    ]
    
    for db_path in possible_dbs:
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 检查所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            print(f"\n📁 数据库: {db_path}")
            print(f"  表数量: {len(tables)}")
            
            # 查找客户相关的表
            customer_tables = []
            for table in tables:
                table_name = table[0]
                if any(keyword in table_name.lower() for keyword in ['customer', 'purchase', 'unit']):
                    customer_tables.append(table_name)
                    
                    # 检查表数据
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    
                    # 显示表结构
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = cursor.fetchall()
                    
                    print(f"  📋 表: {table_name} (记录数: {count})")
                    print(f"    结构: {[col[1] for col in columns]}")
                    
                    # 显示数据内容
                    if count > 0:
                        cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                        rows = cursor.fetchall()
                        print(f"    样本数据:")
                        for i, row in enumerate(rows):
                            print(f"      {i+1}. {row}")
            
            if not customer_tables:
                print("  ❌ 没有找到客户相关表")
            
            conn.close()
            
        except Exception as e:
            print(f"\n📁 数据库: {db_path}")
            print(f"  ❌ 无法连接: {e}")
    
    # 检查后端API返回的数据结构
    print("\n🔍 分析后端API返回的数据结构")
    
    base_url = "http://127.0.0.1:8000"
    
    # 检查/customers API
    response = requests.get(f"{base_url}/api/customers")
    if response.status_code == 200:
        data = response.json()
        customers = data.get("data", [])
        
        print(f"📊 /api/customers 返回 {len(customers)} 个客户")
        if customers:
            print("📋 客户数据结构:")
            for key, value in customers[0].items():
                print(f"  - {key}: {value}")
    
    # 检查/purchase_units API
    response = requests.get(f"{base_url}/api/purchase_units")
    if response.status_code == 200:
        data = response.json()
        units = data.get("data", [])
        
        print(f"\n📊 /api/purchase_units 返回 {len(units)} 个单位")
        if units:
            print("📋 单位数据结构:")
            for key, value in units[0].items():
                print(f"  - {key}: {value}")

def check_backend_service_implementation():
    """检查后端服务实现"""
    
    print("\n🔍 检查后端服务实现")
    print("=" * 60)
    
    # 检查bootstrap.py文件，看看后端使用哪个服务
    bootstrap_file = "e:/FHD/xcagi/app/bootstrap.py"
    
    try:
        with open(bootstrap_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 查找客户服务相关代码
            if "get_customer_import_service" in content:
                print("✅ 找到get_customer_import_service函数")
                
                # 查找函数实现
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if "def get_customer_import_service" in line:
                        print(f"  函数定义在行 {i+1}")
                        # 显示函数实现
                        for j in range(i, min(i+10, len(lines))):
                            print(f"    {lines[j]}")
                        break
            
            # 查找CustomerService相关代码
            if "CustomerService" in content:
                print("\n✅ 找到CustomerService相关代码")
                
    except FileNotFoundError:
        print(f"❌ 文件不存在: {bootstrap_file}")
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
    
    # 检查customer_import_service.py
    service_file = "e:/FHD/xcagi/app/services/customer_import_service.py"
    
    try:
        with open(service_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 查找数据源相关代码
            if "get_all" in content:
                print("\n🔍 检查customer_import_service中的get_all方法")
                
                # 查找数据源
                data_source_patterns = [
                    "Customer.query",
                    "db.session.query",
                    "sqlite3.connect",
                    "purchase_units",
                    "customers"
                ]
                
                for pattern in data_source_patterns:
                    if pattern in content:
                        print(f"  ✅ 使用数据源: {pattern}")
                        
    except FileNotFoundError:
        print(f"❌ 文件不存在: {service_file}")
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")

def fix_backend_data_source():
    """修复后端数据源问题"""
    
    print("\n🔧 修复后端数据源问题")
    print("=" * 60)
    
    # 方案1: 修改后端服务使用正确的数据源
    print("💡 修复方案:")
    print("1. 修改customer_import_service.py，让它从统一的customer数据库获取数据")
    print("2. 或者修改bootstrap.py，让它使用我们修复的CustomerServiceFixed")
    print("3. 重启后端服务使修改生效")
    
    # 检查是否需要创建customer_import_service的修复版
    print("\n📋 需要修改的文件:")
    print("  - e:/FHD/xcagi/app/services/customer_import_service.py")
    print("  - 或者 e:/FHD/xcagi/app/bootstrap.py")
    
    # 检查customer_import_service是否存在
    import os
    service_file = "e:/FHD/xcagi/app/services/customer_import_service.py"
    
    if os.path.exists(service_file):
        print(f"\n✅ customer_import_service.py 存在")
        print("💡 可以修改这个文件来修复数据源")
    else:
        print(f"\n❌ customer_import_service.py 不存在")
        print("💡 需要检查bootstrap.py中的服务配置")

if __name__ == "__main__":
    check_backend_data_source()
    check_backend_service_implementation()
    fix_backend_data_source()
    
    print("\n🎯 下一步行动:")
    print("1. 修改后端服务使用正确的数据源")
    print("2. 重启后端服务")
    print("3. 验证前端客户列表显示正确的数据")