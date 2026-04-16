import sqlite3
import os

def check_databases():
    """检查数据库状态"""
    
    print("🔍 检查数据库状态")
    print("=" * 60)
    
    # 检查所有可能的数据库
    db_paths = [
        "e:/FHD/xcagi/customers.db",
        "e:/FHD/xcagi/products.db",
        "e:/FHD/xcagi/app.db"
    ]
    
    for db_path in db_paths:
        if os.path.exists(db_path):
            print(f"\n📁 数据库：{db_path}")
            
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # 检查所有表
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                print(f"  表数量：{len(tables)}")
                print(f"  表列表：{[table[0] for table in tables]}")
                
                # 检查是否有 materials 表
                if 'materials' in [table[0] for table in tables]:
                    print(f"  ✅ 包含 materials 表")
                    cursor.execute("SELECT COUNT(*) FROM materials WHERE is_active = 1")
                    count = cursor.fetchone()[0]
                    print(f"  活跃原材料数量：{count}")
                else:
                    print(f"  ❌ 不包含 materials 表")
                
                conn.close()
                
            except Exception as e:
                print(f"  ❌ 检查失败：{e}")
        else:
            print(f"\n❌ 数据库不存在：{db_path}")

def check_sqlalchemy_config():
    """检查 SQLAlchemy 配置"""
    
    print("\n🔍 检查 SQLAlchemy 配置")
    print("=" * 60)
    
    # 检查数据库配置文件
    config_file = "e:/FHD/xcagi/app/db/__init__.py"
    
    if os.path.exists(config_file):
        print(f"\n📄 配置文件：{config_file}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 查找数据库路径配置
            if 'get_db_path("customers.db")' in content:
                print("  ⚠️  SQLAlchemy 当前使用 customers.db")
                print("  💡 这会导致 materials 表不存在的问题")
            elif 'get_db_path()' in content:
                print("  ✅ SQLAlchemy 当前使用 products.db")
            else:
                print("  ❓ 未知配置")

def create_materials_table():
    """在 customers.db 中创建 materials 表"""
    
    print("\n🔧 创建 materials 表")
    print("=" * 60)
    
    db_path = "e:/FHD/xcagi/customers.db"
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库不存在：{db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查 materials 表是否已存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='materials'")
        table_exists = cursor.fetchone()
        
        if table_exists:
            print("✅ materials 表已存在")
            conn.close()
            return True
        
        # 创建 materials 表
        create_sql = """
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_code VARCHAR(50) NOT NULL,
            name VARCHAR(255) NOT NULL,
            category VARCHAR(100),
            specification VARCHAR(255),
            unit VARCHAR(50),
            quantity FLOAT DEFAULT 0,
            unit_price FLOAT DEFAULT 0,
            supplier VARCHAR(255),
            warehouse_location VARCHAR(255),
            min_stock FLOAT DEFAULT 0,
            max_stock FLOAT DEFAULT 0,
            description TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        cursor.execute(create_sql)
        conn.commit()
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_materials_code ON materials(material_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_materials_category ON materials(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_materials_is_active ON materials(is_active)")
        conn.commit()
        
        print("✅ materials 表创建成功")
        
        # 验证创建结果
        cursor.execute("SELECT COUNT(*) FROM materials")
        count = cursor.fetchone()[0]
        print(f"  原材料数量：{count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 创建 materials 表失败：{e}")
        return False

def check_other_tables():
    """检查其他可能缺失的表"""
    
    print("\n🔍 检查其他可能缺失的表")
    print("=" * 60)
    
    # 检查 products.db 中有哪些表
    products_db = "e:/FHD/xcagi/products.db"
    customers_db = "e:/FHD/xcagi/customers.db"
    
    if os.path.exists(products_db):
        conn = sqlite3.connect(products_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        products_tables = [table[0] for table in cursor.fetchall()]
        conn.close()
        
        print(f"📊 products.db 中的表：{products_tables}")
    
    if os.path.exists(customers_db):
        conn = sqlite3.connect(customers_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        customers_tables = [table[0] for table in cursor.fetchall()]
        conn.close()
        
        print(f"📊 customers.db 中的表：{customers_tables}")
        
        # 找出缺失的表
        missing_tables = set(products_tables) - set(customers_tables)
        if missing_tables:
            print(f"⚠️ customers.db 缺失的表：{missing_tables}")

if __name__ == "__main__":
    # 检查数据库状态
    check_databases()
    
    # 检查 SQLAlchemy 配置
    check_sqlalchemy_config()
    
    # 创建 materials 表
    create_materials_table()
    
    # 检查其他可能缺失的表
    check_other_tables()
    
    print("\n🎯 解决方案:")
    print("1. 在 customers.db 中创建 materials 表")
    print("2. 或者修改 SQLAlchemy 配置，让不同模块使用不同的数据库")
    print("3. 建议方案：统一使用 products.db 作为主数据库")