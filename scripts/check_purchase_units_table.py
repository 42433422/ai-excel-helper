import sqlite3

def check_purchase_units_table():
    """检查purchase_units表的内容"""
    
    target_db = "e:/FHD/98k/AI助手/AI助手/products.db"
    
    try:
        conn = sqlite3.connect(target_db)
        cursor = conn.cursor()
        
        # 检查purchase_units表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='purchase_units'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("❌ purchase_units表不存在")
            return False
        
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
                print(f"  - ID: {unit[0]}, 名称: {unit[1]}, 联系人: {unit[2]}, 电话: {unit[3]}, 地址: {unit[4]}")
        else:
            print("\n⚠️ purchase_units表中没有活跃的购买单位")
        
        # 检查总购买单位数量（包括非活跃的）
        cursor.execute("SELECT COUNT(*) FROM purchase_units")
        total_units_count = cursor.fetchone()[0]
        print(f"\n📊 总购买单位数量（包括非活跃）: {total_units_count}")
        
        if total_units_count > active_units_count:
            cursor.execute("SELECT * FROM purchase_units WHERE is_active = 0")
            inactive_units = cursor.fetchall()
            print("\n🚫 非活跃的购买单位:")
            for unit in inactive_units:
                print(f"  - ID: {unit[0]}, 名称: {unit[1]}")
        
        conn.close()
        
        return {
            'table_exists': True,
            'active_units': active_units_count,
            'total_units': total_units_count,
            'units_list': units
        }
        
    except Exception as e:
        print(f"❌ 检查purchase_units表时出错: {e}")
        return {'error': str(e)}

def add_bandao_fengqing_to_purchase_units():
    """将半岛风情添加到purchase_units表"""
    
    target_db = "e:/FHD/98k/AI助手/AI助手/products.db"
    
    try:
        conn = sqlite3.connect(target_db)
        cursor = conn.cursor()
        
        # 检查是否已存在半岛风情
        cursor.execute("SELECT id FROM purchase_units WHERE unit_name = ? AND is_active = 1", ("半岛风情",))
        existing_unit = cursor.fetchone()
        
        if existing_unit:
            print("✅ 半岛风情已存在于purchase_units表中")
            return True
        
        # 添加半岛风情到purchase_units表
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
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 添加半岛风情到purchase_units表时出错: {e}")
        return False

if __name__ == "__main__":
    print("🔍 检查purchase_units表")
    print("=" * 50)
    
    # 检查purchase_units表
    result = check_purchase_units_table()
    
    print("\n" + "=" * 50)
    
    if 'error' not in result:
        if result['table_exists']:
            print(f"✅ purchase_units表存在")
            print(f"   活跃购买单位: {result['active_units']} 个")
            print(f"   总购买单位: {result['total_units']} 个")
            
            # 如果半岛风情不在purchase_units表中，则添加
            if result['active_units'] == 2:  # 前端显示2个购买单位
                print("\n🔧 检测到前端显示2个购买单位，正在添加半岛风情...")
                add_success = add_bandao_fengqing_to_purchase_units()
                
                if add_success:
                    print("\n🎉 半岛风情已添加到前端购买单位列表！")
                    print("   刷新前端页面后应该能看到3个购买单位")
                else:
                    print("\n❌ 添加半岛风情失败")
        else:
            print("❌ purchase_units表不存在")
    else:
        print(f"❌ 检查失败: {result['error']}")