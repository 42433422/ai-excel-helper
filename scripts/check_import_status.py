import sqlite3

def check_bandao_import_status():
    """检查半岛风情导入状态"""
    
    target_db = "e:/FHD/98k/AI助手/AI助手/products.db"
    
    try:
        conn = sqlite3.connect(target_db)
        cursor = conn.cursor()
        
        # 检查总产品数量
        cursor.execute("SELECT COUNT(*) FROM products")
        total_count = cursor.fetchone()[0]
        print(f"📊 系统总产品数量: {total_count}")
        
        # 检查半岛风情产品
        cursor.execute("SELECT COUNT(*) FROM products WHERE description LIKE '%半岛风情%'")
        bandao_count = cursor.fetchone()[0]
        print(f"🏝️ 半岛风情产品数量: {bandao_count}")
        
        # 显示半岛风情产品详情
        if bandao_count > 0:
            print("\n📋 半岛风情产品列表:")
            cursor.execute("SELECT id, model_number, name, price, unit, description FROM products WHERE description LIKE '%半岛风情%'")
            products = cursor.fetchall()
            for product in products:
                print(f"  - ID: {product[0]}, 型号: {product[1]}, 名称: {product[2]}, 价格: {product[3]}元/{product[4]}")
                print(f"    描述: {product[5]}")
        else:
            print("⚠️ 未找到标记为'半岛风情'的产品")
            
            # 检查是否有其他产品
            cursor.execute("SELECT COUNT(*) FROM products")
            if cursor.fetchone()[0] > 0:
                print("\n📋 系统中现有的产品:")
                cursor.execute("SELECT id, model_number, name, price, unit, description FROM products LIMIT 10")
                products = cursor.fetchall()
                for product in products:
                    print(f"  - ID: {product[0]}, 型号: {product[1]}, 名称: {product[2]}, 价格: {product[3]}元/{product[4]}")
                    print(f"    描述: {product[5]}")
        
        # 检查数据库文件状态
        import os
        db_size = os.path.getsize(target_db) if os.path.exists(target_db) else 0
        print(f"\n💾 数据库文件大小: {db_size} 字节")
        
        # 检查表结构
        cursor.execute("PRAGMA table_info(products)")
        columns = cursor.fetchall()
        print(f"\n🗂️ 产品表结构 ({len(columns)} 列):")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        conn.close()
        
        return {
            'total_products': total_count,
            'bandao_products': bandao_count,
            'db_size': db_size,
            'success': bandao_count > 0
        }
        
    except Exception as e:
        print(f"❌ 检查导入状态时出错: {e}")
        return {'success': False, 'error': str(e)}

if __name__ == "__main__":
    print("🔍 检查半岛风情导入状态")
    print("=" * 50)
    
    result = check_bandao_import_status()
    
    print("\n" + "=" * 50)
    if result['success']:
        print("✅ 半岛风情导入成功！")
        print(f"   导入产品数量: {result['bandao_products']}")
        print(f"   系统总产品: {result['total_products']}")
    else:
        print("❌ 半岛风情导入未完成或存在问题")
        if 'error' in result:
            print(f"   错误信息: {result['error']}")