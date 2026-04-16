import os
import sqlite3
from app.db.init_db import get_db_path, get_customers_db_path
from app.utils.path_utils import get_app_data_dir

def test_sqlalchemy_config():
    """测试SQLAlchemy数据库配置"""
    
    print("🔍 测试SQLAlchemy数据库配置")
    print("=" * 60)
    
    # 检查应用数据目录
    app_data_dir = get_app_data_dir()
    print(f"📁 应用数据目录: {app_data_dir}")
    
    # 检查数据库文件路径
    products_db_path = get_db_path("products.db")
    customers_db_path = get_customers_db_path()
    
    print(f"📊 products.db路径: {products_db_path}")
    print(f"📊 customers.db路径: {customers_db_path}")
    
    # 检查文件是否存在
    print(f"\n📋 数据库文件状态:")
    print(f"  products.db: {'✅ 存在' if os.path.exists(products_db_path) else '❌ 不存在'}")
    print(f"  customers.db: {'✅ 存在' if os.path.exists(customers_db_path) else '❌ 不存在'}")
    
    # 检查数据库内容
    if os.path.exists(customers_db_path):
        print(f"\n🔍 检查customers.db内容:")
        conn = sqlite3.connect(customers_db_path)
        cursor = conn.cursor()
        
        # 检查所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"  表数量: {len(tables)}")
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  📋 表: {table_name} (记录数: {count})")
            
            # 显示表结构
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print(f"    结构: {[col[1] for col in columns]}")
            
            # 显示数据内容
            if count > 0:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                rows = cursor.fetchall()
                print(f"    样本数据:")
                for i, row in enumerate(rows):
                    print(f"      {i+1}. {row}")
        
        conn.close()
    
    # 检查后端实际使用的数据库
    print(f"\n🔍 检查后端API使用的数据库:")
    
    # 检查后端API返回的数据是否来自这个数据库
    import requests
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
    
    # 检查是否需要修改数据库路径
    print(f"\n💡 问题分析:")
    
    # 检查我们统一的customer数据库路径
    unified_db_path = "e:/FHD/424/customers.db"
    print(f"  统一的customer数据库: {unified_db_path}")
    print(f"  状态: {'✅ 存在' if os.path.exists(unified_db_path) else '❌ 不存在'}")
    
    if os.path.exists(unified_db_path):
        conn = sqlite3.connect(unified_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM purchase_units WHERE is_active = 1")
        count = cursor.fetchone()[0]
        print(f"  活跃购买单位数量: {count}")
        conn.close()
    
    print(f"\n🎯 解决方案:")
    print("  需要修改SQLAlchemy配置，让它使用统一的customer数据库路径")

def check_path_utils():
    """检查路径工具函数"""
    
    print(f"\n🔍 检查路径工具函数")
    print("=" * 60)
    
    from app.utils.path_utils import get_base_dir, get_resource_path
    
    base_dir = get_base_dir()
    resource_path = get_resource_path("db_seed")
    
    print(f"📁 基础目录: {base_dir}")
    print(f"📁 资源路径: {resource_path}")
    
    # 检查db_seed目录
    if os.path.exists(resource_path):
        print(f"📋 db_seed目录内容:")
        for item in os.listdir(resource_path):
            print(f"  - {item}")

if __name__ == "__main__":
    # 添加项目根目录到Python路径
    import sys
    sys.path.insert(0, 'e:/FHD/xcagi')
    
    test_sqlalchemy_config()
    check_path_utils()
    
    print(f"\n📋 总结:")
    print("1. 检查SQLAlchemy使用的数据库路径")
    print("2. 确认后端API数据来源")
    print("3. 修改配置使用统一的customer数据库")