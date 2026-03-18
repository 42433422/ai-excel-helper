#!/usr/bin/env python3
# 更新内部价到数据库（为通用产品设置客户专属价格）

import pandas as pd
import sqlite3
import os

def update_internal_prices():
    """更新内部价到数据库"""
    print("=== 更新内部价到数据库 ===")
    
    # 读取Excel文件
    file_path = "c:\\Users\\97088\\Desktop\\新建文件夹 (4)\\AI助手\\templates\\尹玉华1 - 副本.xlsx"
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return
    
    try:
        # 读取Sheet2
        df = pd.read_excel(file_path, sheet_name='Sheet2')
        df_clean = df.dropna(axis=1, how='all')
        
        # 提取内部价数据
        internal_prices = []
        for i in range(1, min(30, len(df_clean))):
            row = df_clean.iloc[i]
            
            model_number = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
            product_name = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ""
            internal_price = str(row.iloc[2]) if pd.notna(row.iloc[2]) else ""
            
            if not model_number or model_number == "nan" or not product_name or product_name == "nan" or not internal_price or internal_price == "nan":
                continue
            
            try:
                price = float(internal_price)
                internal_prices.append({
                    'model_number': model_number.strip(),
                    'product_name': product_name.strip(),
                    'internal_price': price
                })
            except:
                continue
        
        print(f"提取了 {len(internal_prices)} 个内部价产品")
        for item in internal_prices:
            print(f"  型号: {item['model_number']}, 名称: {item['product_name']}, 内部价: {item['internal_price']}")
        print()
        
        # 连接数据库
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
            return
        
        unit_id = result[0]
        print(f"蕊芯家私1的购买单位ID: {unit_id}")
        
        # 更新/插入客户专属价格
        updated_count = 0
        skipped_count = 0
        
        for item in internal_prices:
            model_number = item['model_number']
            internal_price = item['internal_price']
            
            # 查找对应的产品
            cursor.execute("""
                SELECT id FROM products 
                WHERE model_number = ?
            """, (model_number,))
            
            product_result = cursor.fetchone()
            
            if product_result:
                product_id = product_result[0]
                
                # 检查是否已存在客户专属价格记录
                cursor.execute("""
                    SELECT id FROM customer_products 
                    WHERE unit_id = ? AND product_id = ?
                """, (unit_id, product_id))
                
                cp_result = cursor.fetchone()
                
                if cp_result:
                    # 更新现有记录
                    cursor.execute("""
                        UPDATE customer_products 
                        SET custom_price = ?, updated_at = datetime('now')
                        WHERE id = ?
                    """, (internal_price, cp_result[0]))
                    print(f"  更新: {model_number} → 内部价 {internal_price}")
                else:
                    # 插入新记录
                    cursor.execute("""
                        INSERT INTO customer_products (unit_id, product_id, custom_price, is_active, created_at, updated_at)
                        VALUES (?, ?, ?, 1, datetime('now'), datetime('now'))
                    """, (unit_id, product_id, internal_price))
                    print(f"  新增: {model_number} → 内部价 {internal_price}")
                
                updated_count += 1
            else:
                print(f"  跳过: 未找到型号为 {model_number} 的产品")
                skipped_count += 1
        
        # 提交事务
        conn.commit()
        
        print(f"\n更新完成:")
        print(f"  更新/新增数量: {updated_count}")
        print(f"  跳过数量: {skipped_count}")
        
        # 验证更新结果
        print(f"\n验证更新结果:")
        cursor.execute("""
            SELECT cp.custom_price, p.model_number, p.name
            FROM customer_products cp
            JOIN products p ON cp.product_id = p.id
            WHERE cp.unit_id = ?
            ORDER BY p.model_number
        """, (unit_id,))
        
        updated_products = cursor.fetchall()
        print(f"为蕊芯家私1设置的专属价格产品数量: {len(updated_products)}")
        for product in updated_products:
            print(f"  型号: {product[1]}, 名称: {product[2]}, 专属价: {product[0]}")
        
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ 操作失败: {e}")
        return False

if __name__ == "__main__":
    success = update_internal_prices()
    if success:
        print("\n✅ 内部价更新成功！")
    else:
        print("\n❌ 内部价更新失败！")