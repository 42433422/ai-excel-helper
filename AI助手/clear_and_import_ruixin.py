#!/usr/bin/env python3
# 清理并重新导入蕊芯家私1数据

import pandas as pd
import sqlite3
import os

def clear_and_import_ruixin():
    """清理并重新导入蕊芯家私1数据"""
    print("=== 清理并重新导入蕊芯家私1数据 ===")
    
    # 1. 清理现有数据
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, 'products.db')
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取蕊芯家私1的购买单位ID
        cursor.execute("SELECT id FROM purchase_units WHERE unit_name = ?", ("蕊芯家私1",))
        result = cursor.fetchone()
        
        if not result:
            print("❌ 未找到蕊芯家私1的购买单位")
            conn.close()
            return False
        
        unit_id = result[0]
        print(f"找到蕊芯家私1的购买单位ID: {unit_id}")
        
        # 2. 删除现有的客户专属价格记录
        cursor.execute("""
            SELECT COUNT(*) FROM customer_products WHERE unit_id = ?
        """, (unit_id,))
        
        custom_price_count = cursor.fetchone()[0]
        print(f"删除前: 有 {custom_price_count} 个客户专属价格记录")
        
        if custom_price_count > 0:
            cursor.execute("""
                DELETE FROM customer_products WHERE unit_id = ?
            """, (unit_id,))
            print(f"✅ 已删除 {custom_price_count} 个客户专属价格记录")
        
        # 3. 统计并删除产品记录（如果有专属产品）
        cursor.execute("""
            SELECT COUNT(*) FROM products WHERE purchase_unit_id = ?
        """, (unit_id,))
        
        exclusive_products = cursor.fetchone()[0]
        print(f"删除前: 有 {exclusive_products} 个专属产品记录")
        
        if exclusive_products > 0:
            cursor.execute("""
                DELETE FROM products WHERE purchase_unit_id = ?
            """, (unit_id,))
            print(f"✅ 已删除 {exclusive_products} 个专属产品记录")
        
        # 4. 检查是否有相关产品记录需要删除
        # 这里我们不删除通用产品，只删除专属产品
        # 如果之前有通过products表直接关联的记录，现在也清理
        
        conn.commit()
        conn.close()
        
        print("✅ 现有数据清理完成")
        
    except Exception as e:
        print(f"❌ 清理现有数据失败: {e}")
        return False
    
    # 5. 导入新数据
    try:
        print("\n开始导入新数据...")
        
        # 读取Excel文件
        file_path = "c:\\Users\\97088\\Desktop\\新建文件夹 (4)\\AI助手\\templates\\新建 XLSX 工作表 (2).xlsx"
        df = pd.read_excel(file_path, sheet_name='Sheet1')
        
        # 筛选蕊芯家私1的数据
        ruixin_data = df[df['购买单位'] == '蕊芯家私1'].copy()
        
        print(f"找到 {len(ruixin_data)} 个蕊芯家私1的产品")
        
        if len(ruixin_data) == 0:
            print("❌ 未找到蕊芯家私1的数据")
            return False
        
        # 显示前10个产品
        print("前10个产品:")
        for i, row in ruixin_data.head(10).iterrows():
            print(f"  {row['产品型号']}: {row['产品名称']} - {row['单价']}元")
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 重新插入数据
        inserted_count = 0
        failed_count = 0
        
        for i, row in ruixin_data.iterrows():
            try:
                # 查找或创建产品
                model_number = str(row['产品型号']).strip()
                product_name = str(row['产品名称']).strip()
                price = float(row['单价'])
                
                # 检查是否已存在该产品
                cursor.execute("""
                    SELECT id FROM products WHERE model_number = ? AND name = ?
                """, (model_number, product_name))
                
                existing = cursor.fetchone()
                
                if existing:
                    # 产品已存在，为这个客户创建专属价格记录
                    product_id = existing[0]
                    print(f"  产品已存在: {model_number} - 创建专属价格记录")
                else:
                    # 创建新产品（通用产品）
                    cursor.execute("""
                        INSERT INTO products (model_number, name, specification, price, quantity, description, category, brand, unit, is_active, created_at, updated_at, purchase_unit_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), NULL)
                    """, (model_number, product_name, 25.0, price, 0, "", "", "", "桶", 1))
                    
                    product_id = cursor.lastrowid
                    print(f"  创建新产品: {model_number} - {product_name}")
                
                # 为蕊芯家私1创建专属价格记录
                cursor.execute("""
                    INSERT OR REPLACE INTO customer_products (unit_id, product_id, custom_price, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, 1, datetime('now'), datetime('now'))
                """, (unit_id, product_id, price))
                
                inserted_count += 1
                
            except Exception as e:
                failed_count += 1
                print(f"  ❌ 导入失败: {row['产品型号']} - {str(e)}")
        
        conn.commit()
        conn.close()
        
        print(f"\n✅ 导入完成:")
        print(f"  成功: {inserted_count} 个")
        print(f"  失败: {failed_count} 个")
        
        return True
        
    except Exception as e:
        print(f"❌ 导入新数据失败: {e}")
        return False

if __name__ == "__main__":
    success = clear_and_import_ruixin()
    if success:
        print("\n🎉 蕊芯家私1数据更新成功！")
    else:
        print("\n❌ 蕊芯家私1数据更新失败！")