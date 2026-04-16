import sqlite3
import os

def find_customer_data_source():
    """查找客户数据的实际来源"""
    
    print("🔍 查找客户数据的实际来源")
    print("=" * 50)
    
    # 检查所有可能的数据库文件
    db_files = [
        "e:/FHD/424/customers.db",
        "e:/FHD/98k/AI助手/AI助手/products.db", 
        "e:/FHD/424/database.db",
        "e:/FHD/98k/outputs/database.db"
    ]
    
    for db_file in db_files:
        if os.path.exists(db_file):
            print(f"\n📁 检查数据库: {db_file}")
            
            try:
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                
                # 检查所有表
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                print(f"  表数量: {len(tables)}")
                
                # 查找包含客户数据的表
                customer_tables = []
                for table in tables:
                    table_name = table[0]
                    
                    # 检查表名是否包含客户相关关键词
                    if any(keyword in table_name.lower() for keyword in ['customer', 'client', 'unit', 'purchase']):
                        customer_tables.append(table_name)
                        
                        # 检查表数据
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        count = cursor.fetchone()[0]
                        
                        # 显示前几条记录
                        cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                        sample_data = cursor.fetchall()
                        
                        print(f"  📋 表: {table_name} (记录数: {count})")
                        
                        # 显示表结构
                        cursor.execute(f"PRAGMA table_info({table_name})")
                        columns = cursor.fetchall()
                        print(f"    结构: {[col[1] for col in columns]}")
                        
                        # 显示样本数据
                        if sample_data:
                            print(f"    样本数据:")
                            for i, row in enumerate(sample_data[:2]):
                                print(f"      {i+1}. {row}")
                
                if not customer_tables:
                    print("  ❌ 未找到客户相关表")
                
                conn.close()
                
            except Exception as e:
                print(f"  ❌ 检查数据库时出错: {e}")
    
    # 检查前端可能使用的其他数据源
    print("\n🔍 检查其他可能的数据源:")
    print("  - 前端可能有硬编码的示例数据")
    print("  - 前端可能从API获取数据")
    print("  - 前端可能使用localStorage或sessionStorage")
    print("  - 前端可能有模拟数据")

def check_frontend_customer_data():
    """检查前端客户数据的具体内容"""
    
    print("\n🔍 分析前端客户列表数据")
    print("=" * 50)
    
    # 前端显示的客户数据
    frontend_customers = [
        {"id": 3, "name": "七彩乐园", "contact": "向总", "phone": "-", "address": "-"},
        {"id": 2, "name": "小米公司", "contact": "雷总", "phone": "-", "address": "-"}
    ]
    
    print("📋 前端显示的客户列表:")
    for customer in frontend_customers:
        print(f"  - ID: {customer['id']}, 名称: {customer['name']}, 联系人: {customer['contact']}")
    
    # 检查数据库中是否有这些客户
    print("\n🔍 在数据库中查找这些客户:")
    
    customer_db = "e:/FHD/424/customers.db"
    if os.path.exists(customer_db):
        try:
            conn = sqlite3.connect(customer_db)
            cursor = conn.cursor()
            
            # 检查purchase_units表中是否有这些客户
            cursor.execute("SELECT unit_name, contact_person FROM purchase_units")
            db_customers = cursor.fetchall()
            
            print("  📋 数据库中的客户/购买单位:")
            for customer in db_customers:
                print(f"    - 名称: {customer[0]}, 联系人: {customer[1]}")
            
            # 检查是否有匹配的客户
            matches = []
            for frontend_customer in frontend_customers:
                for db_customer in db_customers:
                    if (frontend_customer['name'] == db_customer[0] or 
                        frontend_customer['contact'] == db_customer[1]):
                        matches.append(frontend_customer['name'])
            
            if matches:
                print(f"\n✅ 找到匹配的客户: {matches}")
            else:
                print("\n❌ 前端客户与数据库中的购买单位不匹配")
                print("💡 前端可能使用不同的数据源或示例数据")
            
            conn.close()
            
        except Exception as e:
            print(f"  ❌ 检查数据库时出错: {e}")
    else:
        print("  ❌ 数据库文件不存在")

if __name__ == "__main__":
    find_customer_data_source()
    check_frontend_customer_data()
    
    print("\n" + "=" * 50)
    print("💡 总结:")
    print("1. 前端显示的是客户列表，不是购买单位列表")
    print("2. 客户数据可能来自不同的数据源")
    print("3. 需要检查前端代码确认客户数据的来源")
    print("4. 购买单位管理应该在专门的页面显示")
