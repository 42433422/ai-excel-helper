#!/usr/bin/env python3
# 提取内部价数据并更新到数据库

import pandas as pd
import sqlite3
import os

def extract_internal_prices():
    """提取内部价数据"""
    print("=== 提取内部价数据 ===")
    
    # 读取Excel文件
    file_path = "c:\\Users\\97088\\Desktop\\新建文件夹 (4)\\AI助手\\templates\\尹玉华1 - 副本.xlsx"
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return
    
    try:
        # 读取Sheet2
        df = pd.read_excel(file_path, sheet_name='Sheet2')
        print(f"Sheet2数据形状: {df.shape}")
        print(f"原始列名: {list(df.columns)}")
        print()
        
        # 清洗数据 - 去除空列
        df_clean = df.dropna(axis=1, how='all')
        print(f"清洗后数据形状: {df_clean.shape}")
        print(f"清洗后列名: {list(df_clean.columns)}")
        print()
        
        # 查看前几行数据
        print("前10行数据:")
        print(df_clean.head(10))
        print()
        
        # 尝试识别产品编号、名称和内部价列
        # 根据数据结构，第0列是产品编号，第1列是产品名称，第2列（实际是第3列）是内部价
        if df_clean.shape[1] >= 3:
            internal_prices = []
            
            for i in range(1, min(30, len(df_clean))):  # 只处理前30行
                row = df_clean.iloc[i]
                
                # 提取数据
                model_number = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
                product_name = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ""
                internal_price = str(row.iloc[2]) if pd.notna(row.iloc[2]) else ""  # 修正：使用第2列而不是第3列
                
                # 跳过空行
                if not model_number or model_number == "nan" or not product_name or product_name == "nan" or not internal_price or internal_price == "nan":
                    continue
                
                # 尝试转换价格为数字
                try:
                    price = float(internal_price)
                except:
                    continue
                
                internal_prices.append({
                    'model_number': model_number.strip(),
                    'product_name': product_name.strip(),
                    'internal_price': price
                })
            
            print("提取的内部价数据:")
            for item in internal_prices:
                print(f"  型号: {item['model_number']}, 名称: {item['product_name']}, 内部价: {item['internal_price']}")
            
            return internal_prices
        else:
            print("❌ 数据列数不足")
            return []
            
    except Exception as e:
        print(f"❌ 读取Excel文件失败: {e}")
        return []

def update_database_prices(internal_prices):
    """更新数据库中的内部价"""
    print("\n=== 更新数据库中的内部价 ===")
    
    if not internal_prices:
        print("❌ 没有内部价数据可更新")
        return
    
    try:
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
        
        # 更新每个产品的内部价
        updated_count = 0
        skipped_count = 0
        
        for item in internal_prices:
            model_number = item['model_number']
            internal_price = item['internal_price']
            
            # 查找对应的产品
            cursor.execute("""
                SELECT id FROM products 
                WHERE model_number = ? AND purchase_unit_id = ?
            """, (model_number, unit_id))
            
            product_result = cursor.fetchone()
            
            if product_result:
                product_id = product_result[0]
                
                # 检查是否已存在客户产品记录
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
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 数据库操作失败: {e}")

if __name__ == "__main__":
    # 提取内部价数据
    internal_prices = extract_internal_prices()
    
    # 更新数据库
    if internal_prices:
        update_database_prices(internal_prices)
    else:
        print("❌ 没有内部价数据可更新")