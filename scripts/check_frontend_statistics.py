import sqlite3

def check_all_statistics():
    """检查所有相关的统计数据"""
    
    customer_db = "e:/FHD/424/customers.db"
    products_db = "e:/FHD/98k/AI助手/AI助手/products.db"
    
    print("🔍 检查所有相关统计数据")
    print("=" * 50)
    
    # 1. 检查customer数据库中的客户数量
    try:
        conn = sqlite3.connect(customer_db)
        cursor = conn.cursor()
        
        # 检查是否有customers表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customers'")
        customers_table_exists = cursor.fetchone()
        
        if customers_table_exists:
            cursor.execute("SELECT COUNT(*) FROM customers WHERE is_active = 1")
            active_customers = cursor.fetchone()[0]
            print(f"👥 活跃客户数量: {active_customers}")
        else:
            print("👥 customers表不存在")
        
        # 检查purchase_units表
        cursor.execute("SELECT COUNT(*) FROM purchase_units WHERE is_active = 1")
        active_units = cursor.fetchone()[0]
        print(f"🏷️ 活跃购买单位数量: {active_units}")
        
        cursor.execute("SELECT unit_name FROM purchase_units WHERE is_active = 1")
        units = cursor.fetchall()
        print(f"   购买单位列表: {[unit[0] for unit in units]}")
        
        conn.close()
    except Exception as e:
        print(f"❌ 检查customer数据库时出错: {e}")
    
    print()
    
    # 2. 检查products数据库中的产品数量
    try:
        conn = sqlite3.connect(products_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM products")
        total_products = cursor.fetchone()[0]
        print(f"📦 总产品数量: {total_products}")
        
        # 按购买单位统计产品数量
        cursor.execute("SELECT description FROM products WHERE description LIKE '%[%]%'")
        descriptions = cursor.fetchall()
        
        unit_counts = {}
        for desc in descriptions:
            import re
            match = re.search(r'\[(.+?)\]', desc[0])
            if match:
                unit_name = match.group(1)
                unit_counts[unit_name] = unit_counts.get(unit_name, 0) + 1
        
        if unit_counts:
            print("📊 按购买单位统计的产品数量:")
            for unit, count in unit_counts.items():
                print(f"  - {unit}: {count} 个产品")
        
        conn.close()
    except Exception as e:
        print(f"❌ 检查products数据库时出错: {e}")
    
    print()
    
    # 3. 检查其他可能的统计数据
    print("📊 其他可能的统计数据:")
    print("  - 客户总数: 可能指customers表中的记录数")
    print("  - 购买单位总数: 可能指purchase_units表中的记录数")
    print("  - 产品总数: 可能指products表中的记录数")
    print("  - 订单总数: 可能在其他表中")
    
    print("\n" + "=" * 50)
    print("💡 建议:")
    print("1. 前端显示的'客户总数：2'可能是指customers表中的客户数量")
    print("2. 购买单位数量应该显示在专门的购买单位管理页面")
    print("3. 检查前端代码确认这个div元素的数据来源")

def add_more_purchase_units():
    """添加更多购买单位用于测试"""
    
    customer_db = "e:/FHD/424/customers.db"
    
    try:
        conn = sqlite3.connect(customer_db)
        cursor = conn.cursor()
        
        # 添加一些测试购买单位
        test_units = [
            "测试单位1",
            "测试单位2", 
            "测试单位3"
        ]
        
        added_count = 0
        for unit_name in test_units:
            # 检查是否已存在
            cursor.execute("SELECT id FROM purchase_units WHERE unit_name = ?", (unit_name,))
            existing = cursor.fetchone()
            
            if not existing:
                cursor.execute("""
                    INSERT INTO purchase_units (unit_name, contact_person, contact_phone, address, is_active)
                    VALUES (?, ?, ?, ?, 1)
                """, (unit_name, "", "", ""))
                added_count += 1
                print(f"✅ 添加购买单位: {unit_name}")
        
        conn.commit()
        
        # 检查添加后的数量
        cursor.execute("SELECT COUNT(*) FROM purchase_units WHERE is_active = 1")
        new_count = cursor.fetchone()[0]
        
        print(f"📊 添加后活跃购买单位数量: {new_count}")
        
        conn.close()
        
        return added_count > 0
        
    except Exception as e:
        print(f"❌ 添加测试购买单位时出错: {e}")
        return False

if __name__ == "__main__":
    # 检查当前统计数据
    check_all_statistics()
    
    print("\n" + "=" * 50)
    print("🧪 添加测试购买单位...")
    
    # 添加测试数据
    success = add_more_purchase_units()
    
    if success:
        print("✅ 测试数据添加完成")
        print("💡 现在刷新前端页面，看看购买单位数量是否变化")
    else:
        print("❌ 测试数据添加失败")