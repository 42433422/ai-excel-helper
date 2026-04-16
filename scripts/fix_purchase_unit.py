import sqlite3

def fix_purchase_unit():
    """将购买单位从'半岛家具'更正为'半岛风情'"""
    
    target_db = "e:/FHD/98k/AI助手/AI助手/products.db"
    
    try:
        conn = sqlite3.connect(target_db)
        cursor = conn.cursor()
        
        # 检查当前标记为'半岛家具'的产品数量
        cursor.execute("SELECT COUNT(*) FROM products WHERE description LIKE '%半岛家具%'")
        current_count = cursor.fetchone()[0]
        print(f"🔍 当前标记为'半岛家具'的产品数量: {current_count}")
        
        if current_count == 0:
            print("⚠️ 未找到标记为'半岛家具'的产品")
            return False
        
        # 更新购买单位标记
        cursor.execute("UPDATE products SET description = REPLACE(description, '[半岛家具]', '[半岛风情]') WHERE description LIKE '%半岛家具%'")
        updated_count = cursor.rowcount
        
        # 提交更改
        conn.commit()
        
        print(f"✅ 成功更新 {updated_count} 个产品的购买单位标记")
        
        # 验证更新结果
        cursor.execute("SELECT COUNT(*) FROM products WHERE description LIKE '%半岛风情%'")
        new_count = cursor.fetchone()[0]
        print(f"🔍 更新后标记为'半岛风情'的产品数量: {new_count}")
        
        # 显示更新后的产品列表
        if new_count > 0:
            print("\n📋 更新后的半岛风情产品列表:")
            cursor.execute("SELECT id, model_number, name, price, unit, description FROM products WHERE description LIKE '%半岛风情%'")
            products = cursor.fetchall()
            for product in products:
                print(f"  - ID: {product[0]}, 型号: {product[1]}, 名称: {product[2]}, 价格: {product[3]}元/{product[4]}")
                print(f"    描述: {product[5]}")
        
        conn.close()
        
        return updated_count > 0
        
    except Exception as e:
        print(f"❌ 修复购买单位时出错: {e}")
        return False

if __name__ == "__main__":
    print("🔧 修复购买单位标记")
    print("=" * 50)
    
    success = fix_purchase_unit()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ 购买单位标记修复完成！")
    else:
        print("❌ 购买单位标记修复失败")