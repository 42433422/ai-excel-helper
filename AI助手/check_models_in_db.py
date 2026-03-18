#!/usr/bin/env python3
# 检查内部价产品在数据库中的情况

import sqlite3
import pandas as pd
import os

def check_models_in_db():
    """检查内部价产品在数据库中的情况"""
    print("=== 检查内部价产品在数据库中的情况 ===")
    
    # 读取内部价数据
    file_path = "c:\\Users\\97088\\Desktop\\新建文件夹 (4)\\AI助手\\templates\\尹玉华1 - 副本.xlsx"
    
    try:
        df = pd.read_excel(file_path, sheet_name='Sheet2')
        df_clean = df.dropna(axis=1, how='all')
        
        # 提取产品型号列表
        internal_models = []
        for i in range(1, min(30, len(df_clean))):
            row = df_clean.iloc[i]
            model_number = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
            if model_number and model_number != "nan":
                internal_models.append(model_number.strip())
        
        print(f"Excel中的产品型号: {internal_models}")
        print()
        
        # 连接数据库
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, 'products.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查每个型号在数据库中的情况
        print("每个型号在数据库中的情况:")
        found_models = []
        not_found_models = []
        
        for model in internal_models:
            cursor.execute("""
                SELECT p.id, p.model_number, p.name, p.purchase_unit_id
                FROM products p
                WHERE p.model_number = ?
                LIMIT 1
            """, (model,))
            
            result = cursor.fetchone()
            if result:
                found_models.append(model)
                print(f"  ✅ {model}: ID={result[0]}, 名称={result[2]}, 专属ID={result[3]}")
            else:
                not_found_models.append(model)
                print(f"  ❌ {model}: 未找到")
        
        print(f"\n总结:")
        print(f"  找到的产品: {len(found_models)}")
        print(f"  未找到的产品: {len(not_found_models)}")
        
        if not_found_models:
            print(f"  未找到的型号: {not_found_models}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == "__main__":
    check_models_in_db()