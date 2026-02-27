#!/usr/bin/env python3
# 分析购买单位和产品的对应关系问题

import sqlite3
import pandas as pd
import os

def analyze_unit_product_mapping():
    """分析购买单位和产品的对应关系"""
    print("=== 分析购买单位和产品的对应关系 ===")
    
    try:
        # 连接数据库
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, 'products.db')
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 分析购买单位
        print("1. 购买单位分析:")
        
        cursor.execute("""
            SELECT id, unit_name
            FROM purchase_units
            ORDER BY unit_name
        """)
        
        units = cursor.fetchall()
        print(f"  总购买单位数: {len(units)}")
        print("  购买单位列表:")
        for unit_id, unit_name in units:
            print(f"    ID: {unit_id}, 名称: {unit_name}")
        
        print()
        
        # 2. 分析购买单位和产品的对应关系
        print("2. 购买单位和产品对应关系分析:")
        
        for unit_id, unit_name in units:
            # 分析专属产品
            cursor.execute("""
                SELECT COUNT(*) 
                FROM products 
                WHERE purchase_unit_id = ? AND is_active = 1
            "", (unit_id,))
            exclusive_count = cursor.fetchone()[0]
            
            # 分析客户专属价
            cursor.execute("""
                SELECT COUNT(*) 
                FROM customer_products 
                WHERE unit_id = ? AND is_active = 1
            "", (unit_id,))
            custom_price_count = cursor.fetchone()[0]
            
            print(f"  {unit_name}:")
            print(f"    专属产品: {exclusive_count}个")
            print(f"    客户专属价: {custom_price_count}个")
        
        print()
        
        # 3. 分析Excel数据和数据库的对应关系
        print("3. Excel数据和数据库对应关系分析:")
        
        excel_path = "c:\\Users\\97088\\Desktop\\新建文件夹 (4)\\AI助手\\templates\\新建 XLSX 工作表 (2).xlsx"
        
        if os.path.exists(excel_path):
            try:
                df = pd.read_excel(excel_path, sheet_name='Sheet1')
                
                # 获取Excel中所有购买单位
                excel_units = df['购买单位'].unique()
                print(f"  Excel中的购买单位数: {len(excel_units)}")
                print("  Excel中的购买单位:")
                for unit in sorted(excel_units):
                    count = len(df[df['购买单位'] == unit])
                    print(f"    {unit}: {count}条数据")
                
                print()
                
                # 分析购买单位对应情况
                print("  购买单位对应情况分析:")
                
                # 数据库中的购买单位名称
                db_unit_names = [unit_name for _, unit_name in units]
                
                # 检查Excel中的购买单位是否在数据库中
                for unit in sorted(excel_units):
                    if unit in db_unit_names:
                        print(f"    ✅ {unit}: 在数据库中存在")
                    else:
                        print(f"    ❌ {unit}: 在数据库中不存在")
                
                print()
                
                # 分析产品型号对应问题
                print("  产品型号对应问题分析:")
                
                # 随机抽取几个购买单位进行分析
                sample_units = ['蕊芯家私1', '七彩乐园', '澜宇']
                
                for unit in sample_units:
                    if unit in excel_units:
                        # 获取Excel中该购买单位的产品
                        excel_products = df[df['购买单位'] == unit]
                        excel_models = excel_products['产品型号'].dropna().unique()
                        
                        print(f"\n    {unit}:")
                        print(f"      Excel产品数: {len(excel_products)}")
                        print(f"      Excel型号数: {len(excel_models)}")
                        print(f"      前5个型号: {list(excel_models[:5])}")
                        
                        # 检查数据库中该购买单位的对应产品
                        if unit in db_unit_names:
                            # 找到数据库中的购买单位ID
                            for db_unit_id, db_unit_name in units:
                                if db_unit_name == unit:
                                    target_unit_id = db_unit_id
                                    break
                            else:
                                target_unit_id = None
                            
                            if target_unit_id:
                                # 检查客户专属价中的产品
                                cursor.execute('''
                                    SELECT p.model_number, COUNT(*)
                                    FROM products p
                                    JOIN customer_products cp ON p.id = cp.product_id
                                    WHERE cp.unit_id = ? AND cp.is_active = 1
                                    GROUP BY p.model_number
                                    ORDER BY COUNT(*) DESC
                                    LIMIT 5
                                ''', (target_unit_id,))
                                
                                db_models = cursor.fetchall()
                                
                                if db_models:
                                    print(f"      数据库中对应型号: {[model[0] for model in db_models]}")
                                else:
                                    print(f"      数据库中无对应型号")
                
            except Exception as e:
                print(f"  ❌ 分析Excel失败: {e}")
        else:
            print(f"  ❌ Excel文件不存在: {excel_path}")
        
        print()
        
        # 4. 分析数据隔离问题
        print("4. 数据隔离问题分析:")
        
        # 检查是否存在购买单位混用的情况
        cursor.execute("""
            SELECT 
                p.model_number, 
                COUNT(DISTINCT cp.unit_id) as unit_count
            FROM products p
            JOIN customer_products cp ON p.id = cp.product_id
            WHERE cp.is_active = 1
            GROUP BY p.model_number
            HAVING COUNT(DISTINCT cp.unit_id) > 1
            ORDER BY unit_count DESC
            LIMIT 10
        """)
        
        shared_models = cursor.fetchall()
        
        if shared_models:
            print("  被多个购买单位共享的产品型号:")
            print(f"  {'产品型号':<15} {'共享购买单位数'}")
            print("  " + "-" * 30)
            for model, unit_count in shared_models:
                print(f"  {model:<15} {unit_count}")
        else:
            print("  ✅ 没有被多个购买单位共享的产品型号")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")

if __name__ == "__main__":
    analyze_unit_product_mapping()