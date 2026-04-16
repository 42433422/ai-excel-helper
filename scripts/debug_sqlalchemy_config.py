import os
import sqlite3
import requests

def debug_sqlalchemy_config():
    """调试SQLAlchemy配置问题"""
    
    print("🔍 调试SQLAlchemy配置问题")
    print("=" * 60)
    
    # 检查后端实际使用的数据库
    print("\n📋 检查后端实际使用的数据库")
    
    # 可能的数据库路径
    db_paths = [
        "e:/FHD/xcagi/products.db",
        "e:/FHD/xcagi/customers.db",
        "e:/FHD/xcagi/app.db",
        "e:/FHD/xcagi/instance/app.db"
    ]
    
    for db_path in db_paths:
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
                            cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
                            rows = cursor.fetchall()
                            print(f"    样本数据:")
                            for i, row in enumerate(rows):
                                print(f"      {i+1}. {row}")
                
                if not customer_tables:
                    print("  ❌ 没有找到客户相关表")
                
                conn.close()
                
            except Exception as e:
                print(f"  ❌ 无法连接: {e}")
    
    # 检查后端API返回的数据来源
    print("\n📋 检查后端API数据来源")
    
    base_url = "http://127.0.0.1:8000"
    
    try:
        response = requests.get(f"{base_url}/api/customers", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            customers = data.get("data", [])
            
            print(f"  📊 /api/customers 返回 {len(customers)} 个客户")
            
            # 检查这些客户在哪个数据库中
            customer_names = [c['customer_name'] for c in customers]
            print(f"  📋 API返回的客户: {customer_names}")
            
            # 在products.db中查找这些客户
            products_db = "e:/FHD/xcagi/products.db"
            if os.path.exists(products_db):
                conn = sqlite3.connect(products_db)
                cursor = conn.cursor()
                
                # 检查customers表
                cursor.execute("SELECT COUNT(*) FROM customers")
                count = cursor.fetchone()[0]
                
                cursor.execute("SELECT id, customer_name FROM customers")
                db_customers = cursor.fetchall()
                
                print(f"\n  🔍 products.db中的customers表:")
                print(f"    记录数: {count}")
                print(f"    客户列表: {[c[1] for c in db_customers]}")
                
                # 检查purchase_units表
                cursor.execute("SELECT COUNT(*) FROM purchase_units WHERE is_active = 1")
                count = cursor.fetchone()[0]
                
                cursor.execute("SELECT id, unit_name FROM purchase_units WHERE is_active = 1")
                db_units = cursor.fetchall()
                
                print(f"\n  🔍 products.db中的purchase_units表:")
                print(f"    活跃记录数: {count}")
                print(f"    购买单位列表: {[u[1] for u in db_units]}")
                
                conn.close()
            
            # 检查customers.db中的purchase_units表
            customers_db = "e:/FHD/xcagi/customers.db"
            if os.path.exists(customers_db):
                conn = sqlite3.connect(customers_db)
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM purchase_units WHERE is_active = 1")
                count = cursor.fetchone()[0]
                
                cursor.execute("SELECT id, unit_name FROM purchase_units WHERE is_active = 1")
                db_units = cursor.fetchall()
                
                print(f"\n  🔍 customers.db中的purchase_units表:")
                print(f"    活跃记录数: {count}")
                print(f"    购买单位列表: {[u[1] for u in db_units]}")
                
                conn.close()
                
    except Exception as e:
        print(f"  ❌ 检查API失败: {e}")
    
    # 检查SQLAlchemy配置
    print("\n📋 检查SQLAlchemy配置")
    
    # 检查customer_import_service.py是否使用了正确的模型
    service_file = "e:/FHD/xcagi/app/services/customer_import_service.py"
    
    if os.path.exists(service_file):
        print(f"\n📄 检查服务文件: {service_file}")
        
        with open(service_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 检查导入的模型
            if "PurchaseUnit" in content:
                print("  ✅ 使用了PurchaseUnit模型")
            else:
                print("  ❌ 没有使用PurchaseUnit模型")
            
            # 检查查询的表
            if "purchase_units" in content:
                print("  ✅ 查询purchase_units表")
            else:
                print("  ❌ 没有查询purchase_units表")
            
            # 检查数据库连接
            if "get_db" in content:
                print("  ✅ 使用了get_db连接")
            else:
                print("  ❌ 没有使用get_db连接")

def check_sqlalchemy_models():
    """检查SQLAlchemy模型"""
    
    print("\n📋 检查SQLAlchemy模型")
    print("=" * 60)
    
    # 检查PurchaseUnit模型
    model_file = "e:/FHD/xcagi/app/db/models/purchase_unit.py"
    
    if os.path.exists(model_file):
        print(f"\n📄 PurchaseUnit模型文件: {model_file}")
        
        with open(model_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            if "__tablename__ = \"purchase_units\"" in content:
                print("  ✅ 模型映射到purchase_units表")
            else:
                print("  ❌ 模型没有正确映射到purchase_units表")
            
            if "unit_name" in content:
                print("  ✅ 模型包含unit_name字段")
            else:
                print("  ❌ 模型不包含unit_name字段")
    
    # 检查模型是否被正确导入
    init_file = "e:/FHD/xcagi/app/db/models/__init__.py"
    
    if os.path.exists(init_file):
        print(f"\n📄 模型初始化文件: {init_file}")
        
        with open(init_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            if "PurchaseUnit" in content:
                print("  ✅ PurchaseUnit模型已导入")
            else:
                print("  ❌ PurchaseUnit模型未导入")

if __name__ == "__main__":
    debug_sqlalchemy_config()
    check_sqlalchemy_models()
    
    print("\n🎯 问题分析:")
    print("1. 后端API返回的数据来自products.db的customers表")
    print("2. 我们需要让后端使用customers.db的purchase_units表")
    print("3. 需要修改customer_import_service.py的查询逻辑")