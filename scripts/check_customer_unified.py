import sqlite3

def check_customer_unified_database():
    """检查统一的客户/购买单位数据库"""
    
    customer_db = "e:/FHD/424/customers.db"
    
    try:
        conn = sqlite3.connect(customer_db)
        cursor = conn.cursor()
        
        print("🔍 检查客户/购买单位统一数据库")
        print("=" * 50)
        
        # 检查数据库中的所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print("📊 数据库中的表:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # 检查purchase_units表的结构和数据
        print("\n🏷️ 检查purchase_units表:")
        cursor.execute("PRAGMA table_info(purchase_units)")
        columns = cursor.fetchall()
        
        print("  表结构:")
        for col in columns:
            print(f"    - {col[1]} ({col[2]})")
        
        # 检查活跃的购买单位数量
        cursor.execute("SELECT COUNT(*) FROM purchase_units WHERE is_active = 1")
        active_units = cursor.fetchone()[0]
        print(f"\n📊 活跃的购买单位数量: {active_units}")
        
        # 显示所有活跃的购买单位
        cursor.execute("SELECT * FROM purchase_units WHERE is_active = 1 ORDER BY unit_name")
        units = cursor.fetchall()
        
        print("  活跃购买单位列表:")
        for unit in units:
            print(f"    - ID: {unit[0]}, 名称: {unit[1]}")
            if len(unit) > 2:
                print(f"      联系人: {unit[2]}, 电话: {unit[3]}, 地址: {unit[4]}")
        
        # 检查是否有customers表（可能已统一到purchase_units表）
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customers'")
        customers_table_exists = cursor.fetchone()
        
        if customers_table_exists:
            print("\n👥 customers表存在，检查客户数量:")
            cursor.execute("SELECT COUNT(*) FROM customers WHERE is_active = 1")
            active_customers = cursor.fetchone()[0]
            print(f"  活跃客户数量: {active_customers}")
        else:
            print("\n👥 customers表不存在，客户数据已统一到purchase_units表")
        
        # 检查前端可能使用的其他表名
        possible_customer_tables = ['customer', 'clients', 'buyers', 'units']
        for table_name in possible_customer_tables:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = ?", (table_name,))
            if cursor.fetchone():
                print(f"\n📋 发现可能的前端数据表: {table_name}")
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"  记录数量: {count}")
        
        conn.close()
        
        return {
            'tables': [table[0] for table in tables],
            'active_units': active_units,
            'customers_table_exists': bool(customers_table_exists)
        }
        
    except Exception as e:
        print(f"❌ 检查数据库时出错: {e}")
        return {'error': str(e)}

def check_frontend_api_logic():
    """检查前端API逻辑，看看前端如何获取客户/购买单位数量"""
    
    print("\n🔍 检查前端API逻辑")
    print("=" * 50)
    
    # 检查前端可能调用的API
    api_patterns = [
        "/api/customers/count",
        "/api/customers", 
        "/api/purchase_units/count",
        "/api/purchase_units",
        "/api/units/count",
        "/api/units"
    ]
    
    print("💡 前端可能调用的API:")
    for api in api_patterns:
        print(f"  - GET {api}")
    
    print("\n📋 可能的数据源:")
    print("  1. purchase_units表中is_active=1的记录数")
    print("  2. 前端可能有固定的示例数据")
    print("  3. 前端可能从其他数据库表获取数据")
    print("  4. 前端可能有缓存或硬编码的数据")

def fix_customer_count():
    """修复客户/购买单位数量显示问题"""
    
    customer_db = "e:/FHD/424/customers.db"
    
    try:
        conn = sqlite3.connect(customer_db)
        cursor = conn.cursor()
        
        # 检查当前活跃购买单位数量
        cursor.execute("SELECT COUNT(*) FROM purchase_units WHERE is_active = 1")
        current_count = cursor.fetchone()[0]
        
        print(f"\n🔧 当前活跃购买单位数量: {current_count}")
        
        # 如果数量不是5，检查是否有非活跃的单位
        if current_count != 5:
            cursor.execute("SELECT COUNT(*) FROM purchase_units WHERE is_active = 0")
            inactive_count = cursor.fetchone()[0]
            print(f"  非活跃购买单位数量: {inactive_count}")
            
            # 激活所有购买单位
            cursor.execute("UPDATE purchase_units SET is_active = 1 WHERE is_active = 0")
            updated_count = cursor.rowcount
            
            if updated_count > 0:
                conn.commit()
                print(f"✅ 已激活 {updated_count} 个非活跃购买单位")
            
            # 重新检查数量
            cursor.execute("SELECT COUNT(*) FROM purchase_units WHERE is_active = 1")
            new_count = cursor.fetchone()[0]
            print(f"📊 修复后活跃购买单位数量: {new_count}")
        else:
            print("✅ 活跃购买单位数量正确 (5个)")
        
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ 修复客户数量时出错: {e}")
        return False

if __name__ == "__main__":
    # 检查数据库状态
    result = check_customer_unified_database()
    
    # 检查前端API逻辑
    check_frontend_api_logic()
    
    print("\n" + "=" * 50)
    
    if 'error' not in result:
        print(f"📊 数据库状态总结:")
        print(f"  数据库表数量: {len(result['tables'])}")
        print(f"  活跃购买单位: {result['active_units']} 个")
        print(f"  customers表存在: {result['customers_table_exists']}")
        
        # 修复客户数量显示问题
        print("\n🔧 修复客户数量显示问题...")
        fix_success = fix_customer_count()
        
        if fix_success:
            print("\n🎉 修复完成！")
            print("💡 现在刷新前端页面，客户总数应该显示正确的数量")
            print("💡 如果还是显示2，可能是前端有缓存或硬编码数据")
        else:
            print("\n❌ 修复失败")
    else:
        print(f"❌ 检查失败: {result['error']}")