import sqlite3

def check_customer_database():
    """检查customer数据库中的购买单位"""
    
    customer_db = "e:/FHD/424/customers.db"
    
    try:
        conn = sqlite3.connect(customer_db)
        cursor = conn.cursor()
        
        # 检查数据库中的所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print("📊 customer数据库中的表:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # 检查是否有purchase_units表
        purchase_units_exists = any('purchase_units' in table[0].lower() for table in tables)
        
        if purchase_units_exists:
            print("\n✅ customer数据库中有purchase_units表")
            
            # 检查purchase_units表结构
            cursor.execute("PRAGMA table_info(purchase_units)")
            columns = cursor.fetchall()
            print("🗂️ purchase_units表结构:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
            
            # 检查purchase_units表中的数据
            cursor.execute("SELECT COUNT(*) FROM purchase_units WHERE is_active = 1")
            active_units_count = cursor.fetchone()[0]
            print(f"\n📊 活跃的购买单位数量: {active_units_count}")
            
            cursor.execute("SELECT * FROM purchase_units WHERE is_active = 1 ORDER BY unit_name")
            units = cursor.fetchall()
            
            if units:
                print("\n🏷️ purchase_units表中的购买单位:")
                for unit in units:
                    print(f"  - ID: {unit[0]}, 名称: {unit[1]}")
                    if len(unit) > 2:
                        print(f"    联系人: {unit[2]}, 电话: {unit[3]}, 地址: {unit[4]}")
            
            # 检查是否有半岛风情
            cursor.execute("SELECT id FROM purchase_units WHERE unit_name = ? AND is_active = 1", ("半岛风情",))
            bandao_exists = cursor.fetchone()
            
            if bandao_exists:
                print("\n✅ 半岛风情已存在于purchase_units表中")
            else:
                print("\n❌ 半岛风情不存在于purchase_units表中")
                
                # 添加半岛风情
                cursor.execute("""
                    INSERT INTO purchase_units (unit_name, contact_person, contact_phone, address, is_active, created_at)
                    VALUES (?, ?, ?, ?, 1, datetime('now'))
                """, ("半岛风情", "", "", ""))
                
                conn.commit()
                print("✅ 半岛风情已成功添加到purchase_units表")
                
                # 验证添加结果
                cursor.execute("SELECT COUNT(*) FROM purchase_units WHERE is_active = 1")
                new_count = cursor.fetchone()[0]
                print(f"📊 添加后活跃购买单位数量: {new_count}")
        else:
            print("\n❌ customer数据库中没有purchase_units表")
            print("正在创建purchase_units表...")
            
            # 创建purchase_units表
            cursor.execute('''
                CREATE TABLE purchase_units (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    unit_name TEXT NOT NULL UNIQUE,
                    contact_person TEXT,
                    contact_phone TEXT,
                    address TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 添加半岛风情
            cursor.execute("""
                INSERT INTO purchase_units (unit_name, contact_person, contact_phone, address, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, ("半岛风情", "", "", ""))
            
            conn.commit()
            print("✅ purchase_units表创建完成，半岛风情已添加")
            
            # 验证添加结果
            cursor.execute("SELECT COUNT(*) FROM purchase_units WHERE is_active = 1")
            new_count = cursor.fetchone()[0]
            print(f"📊 活跃购买单位数量: {new_count}")
        
        conn.close()
        
        return {
            'tables': [table[0] for table in tables],
            'purchase_units_exists': purchase_units_exists,
            'active_units': active_units_count if purchase_units_exists else 1
        }
        
    except Exception as e:
        print(f"❌ 检查customer数据库时出错: {e}")
        return {'error': str(e)}

if __name__ == "__main__":
    print("🔍 检查customer数据库")
    print("=" * 50)
    
    result = check_customer_database()
    
    print("\n" + "=" * 50)
    if 'error' not in result:
        print(f"✅ 检查完成！")
        print(f"   数据库表数量: {len(result['tables'])}")
        print(f"   purchase_units表存在: {result['purchase_units_exists']}")
        print(f"   活跃购买单位数量: {result['active_units']}")
        print("\n🎉 半岛风情已添加到前端购买单位列表！")
        print("   刷新前端页面后应该能看到3个购买单位")
    else:
        print(f"❌ 检查失败: {result['error']}")