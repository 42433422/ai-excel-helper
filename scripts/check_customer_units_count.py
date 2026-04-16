import sqlite3

def check_customer_units_count():
    """检查customer数据库中的购买单位数量"""
    
    customer_db = "e:/FHD/424/customers.db"
    
    try:
        conn = sqlite3.connect(customer_db)
        cursor = conn.cursor()
        
        # 检查purchase_units表中的活跃购买单位数量
        cursor.execute("SELECT COUNT(*) FROM purchase_units WHERE is_active = 1")
        active_units_count = cursor.fetchone()[0]
        
        # 检查所有购买单位
        cursor.execute("SELECT * FROM purchase_units WHERE is_active = 1 ORDER BY unit_name")
        units = cursor.fetchall()
        
        print(f"📊 customer数据库中活跃购买单位数量: {active_units_count}")
        
        if units:
            print("\n🏷️ 活跃的购买单位列表:")
            for unit in units:
                print(f"  - ID: {unit[0]}, 名称: {unit[1]}")
                if len(unit) > 2:
                    print(f"    联系人: {unit[2]}, 电话: {unit[3]}, 地址: {unit[4]}")
        
        # 检查非活跃的购买单位
        cursor.execute("SELECT COUNT(*) FROM purchase_units WHERE is_active = 0")
        inactive_units_count = cursor.fetchone()[0]
        
        if inactive_units_count > 0:
            print(f"\n🚫 非活跃的购买单位数量: {inactive_units_count}")
            cursor.execute("SELECT * FROM purchase_units WHERE is_active = 0")
            inactive_units = cursor.fetchall()
            for unit in inactive_units:
                print(f"  - ID: {unit[0]}, 名称: {unit[1]}")
        
        # 检查总购买单位数量
        cursor.execute("SELECT COUNT(*) FROM purchase_units")
        total_units_count = cursor.fetchone()[0]
        print(f"\n📊 总购买单位数量: {total_units_count}")
        
        # 检查是否有半岛风情
        cursor.execute("SELECT id FROM purchase_units WHERE unit_name = '半岛风情' AND is_active = 1")
        bandao_exists = cursor.fetchone()
        
        if bandao_exists:
            print("✅ 半岛风情存在于活跃购买单位中")
        else:
            print("❌ 半岛风情不存在于活跃购买单位中")
            
            # 检查是否存在于非活跃状态
            cursor.execute("SELECT id FROM purchase_units WHERE unit_name = '半岛风情' AND is_active = 0")
            bandao_inactive = cursor.fetchone()
            if bandao_inactive:
                print("⚠️ 半岛风情存在于非活跃购买单位中")
        
        conn.close()
        
        return {
            'active_units': active_units_count,
            'total_units': total_units_count,
            'bandao_exists': bool(bandao_exists)
        }
        
    except Exception as e:
        print(f"❌ 检查购买单位数量时出错: {e}")
        return {'error': str(e)}

def fix_bandao_fengqing_status():
    """修复半岛风情的状态"""
    
    customer_db = "e:/FHD/424/customers.db"
    
    try:
        conn = sqlite3.connect(customer_db)
        cursor = conn.cursor()
        
        # 检查半岛风情的状态
        cursor.execute("SELECT id, is_active FROM purchase_units WHERE unit_name = '半岛风情'")
        bandao_info = cursor.fetchone()
        
        if bandao_info:
            unit_id, is_active = bandao_info
            if is_active == 0:
                # 激活半岛风情
                cursor.execute("UPDATE purchase_units SET is_active = 1 WHERE id = ?", (unit_id,))
                conn.commit()
                print("✅ 半岛风情已激活")
            else:
                print("✅ 半岛风情已经是活跃状态")
        else:
            # 添加半岛风情
            cursor.execute("""
                INSERT INTO purchase_units (unit_name, contact_person, contact_phone, address, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, ("半岛风情", "", "", ""))
            conn.commit()
            print("✅ 半岛风情已添加到活跃购买单位")
        
        # 验证修复结果
        cursor.execute("SELECT COUNT(*) FROM purchase_units WHERE is_active = 1")
        new_count = cursor.fetchone()[0]
        print(f"📊 修复后活跃购买单位数量: {new_count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 修复半岛风情状态时出错: {e}")
        return False

if __name__ == "__main__":
    print("🔍 检查customer数据库购买单位数量")
    print("=" * 50)
    
    # 检查当前状态
    result = check_customer_units_count()
    
    print("\n" + "=" * 50)
    
    if 'error' not in result:
        print(f"📊 当前状态:")
        print(f"   活跃购买单位: {result['active_units']} 个")
        print(f"   总购买单位: {result['total_units']} 个")
        print(f"   半岛风情存在: {result['bandao_exists']}")
        
        # 如果活跃购买单位不是3个，进行修复
        if result['active_units'] != 3 or not result['bandao_exists']:
            print("\n🔧 检测到购买单位数量不正确，正在修复...")
            fix_success = fix_bandao_fengqing_status()
            
            if fix_success:
                print("\n🎉 修复完成！")
                print("   刷新前端页面后应该能看到3个购买单位")
            else:
                print("\n❌ 修复失败")
        else:
            print("\n✅ 购买单位数量正确，前端应该显示3个购买单位")
    else:
        print(f"❌ 检查失败: {result['error']}")