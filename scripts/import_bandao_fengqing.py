import sqlite3
import os
from datetime import datetime

def import_bandao_fengqing():
    """导入半岛风情购买单位和产品数据"""
    
    # 数据库路径
    source_db = "e:/FHD/424/半岛风情.db"
    target_db = "e:/FHD/98k/AI助手/AI助手/products.db"
    
    print("=== 开始导入半岛风情购买单位和产品数据 ===")
    
    # 检查源数据库
    if not os.path.exists(source_db):
        print(f"错误: 源数据库文件不存在: {source_db}")
        return False
    
    # 检查目标数据库
    if not os.path.exists(target_db):
        print(f"错误: 目标数据库文件不存在: {target_db}")
        return False
    
    try:
        # 连接源数据库
        source_conn = sqlite3.connect(source_db)
        source_cursor = source_conn.cursor()
        
        # 连接目标数据库
        target_conn = sqlite3.connect(target_db)
        target_cursor = target_conn.cursor()
        
        # 检查目标数据库结构
        target_cursor.execute("PRAGMA table_info(products)")
        target_columns = [col[1] for col in target_cursor.fetchall()]
        print(f"目标数据库列结构: {target_columns}")
        
        # 检查源数据库数据
        source_cursor.execute("SELECT COUNT(*) FROM products")
        source_count = source_cursor.fetchone()[0]
        print(f"源数据库产品数量: {source_count}")
        
        if source_count == 0:
            print("源数据库中没有产品数据，跳过导入")
            return True
        
        # 获取源数据库产品数据
        source_cursor.execute("SELECT * FROM products")
        source_products = source_cursor.fetchall()
        
        # 检查目标数据库中是否已存在相同型号的产品
        imported_count = 0
        skipped_count = 0
        
        for product in source_products:
            # 源数据库结构: id, model_number, name, specification, price, quantity, description, category, brand, unit, is_active, created_at, updated_at
            source_id, model_number, name, specification, price, quantity, description, category, brand, unit, is_active, created_at, updated_at = product
            
            # 检查目标数据库中是否已存在相同型号的产品
            target_cursor.execute("SELECT id FROM products WHERE model_number = ?", (model_number,))
            existing_product = target_cursor.fetchone()
            
            if existing_product:
                print(f"跳过已存在的产品: {model_number} - {name}")
                skipped_count += 1
                continue
            
            # 插入新产品，添加购买单位标识
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 构建插入语句
            insert_sql = """
            INSERT INTO products (model_number, name, specification, price, quantity, description, category, brand, unit, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            # 在描述中添加购买单位标识
            description_with_unit = f"[半岛风情] {description if description else ''}".strip()
            
            target_cursor.execute(insert_sql, (
                model_number, name, specification, price, quantity, 
                description_with_unit, category, brand, unit, is_active,
                current_time, current_time
            ))
            
            print(f"导入产品: {model_number} - {name}")
            imported_count += 1
        
        # 提交事务
        target_conn.commit()
        
        print(f"\n=== 导入完成 ===")
        print(f"成功导入: {imported_count} 个产品")
        print(f"跳过已存在: {skipped_count} 个产品")
        print(f"购买单位: 半岛风情")
        
        # 验证导入结果
        target_cursor.execute("SELECT COUNT(*) FROM products WHERE description LIKE '%半岛风情%'")
        verified_count = target_cursor.fetchone()[0]
        print(f"验证结果: 系统中现有 {verified_count} 个半岛风情产品")
        
        # 关闭连接
        source_conn.close()
        target_conn.close()
        
        return True
        
    except Exception as e:
        print(f"导入过程中出错: {e}")
        return False

def check_import_result():
    """检查导入结果"""
    target_db = "e:/FHD/98k/AI助手/AI助手/products.db"
    
    try:
        conn = sqlite3.connect(target_db)
        cursor = conn.cursor()
        
        # 检查所有产品
        cursor.execute("SELECT COUNT(*) FROM products")
        total_count = cursor.fetchone()[0]
        print(f"\n=== 系统产品统计 ===")
        print(f"总产品数量: {total_count}")
        
        # 检查半岛风情产品
        cursor.execute("SELECT COUNT(*) FROM products WHERE description LIKE '%半岛风情%'")
        bandao_count = cursor.fetchone()[0]
        print(f"半岛风情产品数量: {bandao_count}")
        
        # 显示半岛风情产品列表
        if bandao_count > 0:
            print("\n半岛风情产品列表:")
            cursor.execute("SELECT model_number, name, price, unit FROM products WHERE description LIKE '%半岛风情%'")
            products = cursor.fetchall()
            for product in products:
                print(f"  - {product[0]}: {product[1]} ({product[2]}元/{product[3]})")
        
        # 检查购买单位分布
        print("\n购买单位分布:")
        cursor.execute("SELECT DISTINCT unit FROM products")
        units = cursor.fetchall()
        for unit in units:
            cursor.execute("SELECT COUNT(*) FROM products WHERE unit = ?", (unit[0],))
            count = cursor.fetchone()[0]
            print(f"  - {unit[0]}: {count} 个产品")
        
        conn.close()
        
    except Exception as e:
        print(f"检查导入结果时出错: {e}")

if __name__ == "__main__":
    print("半岛风情购买单位导入工具")
    print("=" * 50)
    
    # 执行导入
    success = import_bandao_fengqing()
    
    if success:
        # 检查导入结果
        check_import_result()
        print("\n✅ 导入完成!")
    else:
        print("\n❌ 导入失败!")