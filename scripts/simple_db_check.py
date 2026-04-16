import os
import sqlite3
import requests

def simple_db_check():
    """简单检查数据库配置"""
    
    print("🔍 简单检查数据库配置")
    print("=" * 60)
    
    # 检查后端API使用的数据库
    print("\n📋 检查后端API使用的数据库:")
    
    base_url = "http://127.0.0.1:8000"
    
    response = requests.get(f"{base_url}/api/customers")
    if response.status_code == 200:
        data = response.json()
        customers = data.get("data", [])
        
        print(f"  📊 /api/customers 返回 {len(customers)} 个客户")
        if customers:
            print("  📋 客户列表:")
            for customer in customers:
                print(f"    - ID: {customer['id']}, 名称: {customer['customer_name']}")
    
    # 检查可能的数据库路径
    print("\n📋 检查可能的数据库路径:")
    
    possible_dbs = [
        "e:/FHD/xcagi/app.db",
        "e:/FHD/xcagi/instance/app.db",
        "e:/FHD/xcagi/data/app.db",
        "e:/FHD/xcagi/app/data/products.db",
        "e:/FHD/xcagi/app/data/customers.db",
        "e:/FHD/xcagi/products.db",
        "e:/FHD/xcagi/customers.db",
        "e:/FHD/424/customers.db",
        "e:/FHD/98k/AI助手/AI助手/products.db"
    ]
    
    for db_path in possible_dbs:
        if os.path.exists(db_path):
            print(f"\n📁 数据库: {db_path}")
            
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # 检查所有表
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
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
                        
                        print(f"  📋 表: {table_name} (记录数: {count})")
                        
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
                print(f"  ❌ 无法连接: {e}")
    
    # 检查我们统一的customer数据库
    print("\n📋 检查统一的customer数据库:")
    
    unified_db = "e:/FHD/424/customers.db"
    if os.path.exists(unified_db):
        print(f"📁 统一的customer数据库: {unified_db}")
        
        conn = sqlite3.connect(unified_db)
        cursor = conn.cursor()
        
        # 检查purchase_units表
        cursor.execute("SELECT COUNT(*) FROM purchase_units WHERE is_active = 1")
        active_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT id, unit_name FROM purchase_units WHERE is_active = 1 ORDER BY unit_name")
        units = cursor.fetchall()
        
        print(f"  📊 活跃购买单位: {active_count} 个")
        print("  🏷️ 购买单位列表:")
        for unit in units:
            print(f"    - ID: {unit[0]}, 名称: {unit[1]}")
        
        conn.close()
    else:
        print(f"❌ 统一的customer数据库不存在: {unified_db}")
    
    print("\n🎯 问题分析:")
    print("1. 后端API返回的是示例数据（七彩乐园、小米公司）")
    print("2. 统一的customer数据库中有5个购买单位")
    print("3. 需要修改SQLAlchemy配置使用正确的数据库路径")

def check_sqlalchemy_config():
    """检查SQLAlchemy配置"""
    
    print("\n🔍 检查SQLAlchemy配置")
    print("=" * 60)
    
    # 检查xcagi目录下的数据库配置文件
    config_files = [
        "e:/FHD/xcagi/app/db/__init__.py",
        "e:/FHD/xcagi/app/db/session.py",
        "e:/FHD/xcagi/app/db/init_db.py"
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"\n📄 配置文件: {config_file}")
            
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # 查找数据库路径配置
                    path_patterns = [
                        "get_db_path",
                        "customers.db",
                        "products.db",
                        "sqlite:///",
                        "get_app_data_dir"
                    ]
                    
                    for pattern in path_patterns:
                        if pattern in content:
                            print(f"  ✅ 找到配置: {pattern}")
                            
                            # 显示相关代码行
                            lines = content.split('\n')
                            for i, line in enumerate(lines):
                                if pattern in line:
                                    print(f"    行 {i+1}: {line.strip()}")
                                    
            except Exception as e:
                print(f"  ❌ 读取失败: {e}")

if __name__ == "__main__":
    simple_db_check()
    check_sqlalchemy_config()
    
    print("\n💡 解决方案:")
    print("1. 修改SQLAlchemy配置，让它使用 e:/FHD/424/customers.db")
    print("2. 或者修改数据库路径配置，指向正确的数据库")
    print("3. 重启后端服务")