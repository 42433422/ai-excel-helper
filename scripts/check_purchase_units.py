import sqlite3

def check_all_purchase_units():
    """检查系统中所有的购买单位"""
    
    target_db = "e:/FHD/98k/AI助手/AI助手/products.db"
    
    try:
        conn = sqlite3.connect(target_db)
        cursor = conn.cursor()
        
        # 检查总产品数量
        cursor.execute("SELECT COUNT(*) FROM products")
        total_count = cursor.fetchone()[0]
        print(f"📊 系统总产品数量: {total_count}")
        
        # 获取所有不同的购买单位（从description字段中提取）
        cursor.execute("SELECT DISTINCT description FROM products WHERE description LIKE '%[%]%'")
        descriptions = cursor.fetchall()
        
        print(f"\n🏷️ 系统中存在的购买单位:")
        
        purchase_units = []
        for desc in descriptions:
            # 从描述中提取购买单位名称
            import re
            match = re.search(r'\[(.+?)\]', desc[0])
            if match:
                unit_name = match.group(1)
                
                # 统计该购买单位的产品数量
                cursor.execute("SELECT COUNT(*) FROM products WHERE description LIKE ?", (f'%[{unit_name}]%',))
                unit_count = cursor.fetchone()[0]
                
                purchase_units.append((unit_name, unit_count))
                print(f"  - {unit_name}: {unit_count} 个产品")
        
        # 如果没有找到购买单位标记，检查所有产品描述
        if not purchase_units:
            print("  ⚠️ 未找到明确的购买单位标记")
            
            # 显示所有产品的描述
            cursor.execute("SELECT description FROM products WHERE description IS NOT NULL AND description != ''")
            all_descriptions = cursor.fetchall()
            
            if all_descriptions:
                print("\n📝 所有产品描述:")
                for desc in all_descriptions:
                    print(f"  - {desc[0]}")
        
        # 检查没有购买单位标记的产品
        cursor.execute("SELECT COUNT(*) FROM products WHERE description IS NULL OR description = '' OR description NOT LIKE '%[%]%'")
        no_unit_count = cursor.fetchone()[0]
        
        if no_unit_count > 0:
            print(f"\n⚠️ 没有购买单位标记的产品: {no_unit_count} 个")
        
        # 显示所有产品列表
        print(f"\n📋 系统中所有产品列表:")
        cursor.execute("SELECT id, model_number, name, price, unit, description FROM products")
        products = cursor.fetchall()
        
        for product in products:
            print(f"  - ID: {product[0]}, 型号: {product[1]}, 名称: {product[2]}, 价格: {product[3]}元/{product[4]}")
            print(f"    描述: {product[5]}")
        
        conn.close()
        
        return {
            'total_products': total_count,
            'purchase_units': purchase_units,
            'products_without_units': no_unit_count
        }
        
    except Exception as e:
        print(f"❌ 检查购买单位时出错: {e}")
        return {'error': str(e)}

if __name__ == "__main__":
    print("🔍 检查系统中所有购买单位")
    print("=" * 50)
    
    result = check_all_purchase_units()
    
    print("\n" + "=" * 50)
    if 'error' not in result:
        print(f"✅ 检查完成！")
        print(f"   总产品数量: {result['total_products']}")
        print(f"   购买单位数量: {len(result['purchase_units'])}")
        if result['purchase_units']:
            print(f"   购买单位列表: {[unit[0] for unit in result['purchase_units']]}")
        if result['products_without_units'] > 0:
            print(f"   无购买单位标记的产品: {result['products_without_units']}")
    else:
        print(f"❌ 检查失败: {result['error']}")