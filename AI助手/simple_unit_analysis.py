#!/usr/bin/env python3
# 简单分析购买单位和产品对应关系

import sqlite3
import pandas as pd
import os

def simple_unit_analysis():
    """简单分析购买单位和产品对应关系"""
    print("=== 分析购买单位和产品对应关系 ===")
    
    try:
        # 连接数据库
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, 'products.db')
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 获取购买单位
        cursor.execute("SELECT id, unit_name FROM purchase_units ORDER BY unit_name")
        units = cursor.fetchall()
        print(f"1. 购买单位列表 ({len(units)}个):")
        for unit_id, unit_name in units:
            print(f"   {unit_id}: {unit_name}")
        
        print()
        
        # 2. 分析Excel数据
        print("2. Excel数据分析:")
        
        excel_path = "c:\\Users\\97088\\Desktop\\新建文件夹 (4)\\AI助手\\templates\\新建 XLSX 工作表 (2).xlsx"
        
        if os.path.exists(excel_path):
            try:
                df = pd.read_excel(excel_path, sheet_name='Sheet1')
                excel_units = df['购买单位'].unique()
                
                print(f"   Excel购买单位数: {len(excel_units)}")
                print(f"   Excel总数据数: {len(df)}")
                
                # 显示前几个购买单位
                print("   前5个购买单位及其数据量:")
                for unit in sorted(excel_units)[:5]:
                    count = len(df[df['购买单位'] == unit])
                    print(f"     {unit}: {count}条")
                
                print()
                
                # 3. 分析购买单位对应问题
                print("3. 购买单位对应分析:")
                
                # 数据库中的购买单位名称
                db_unit_names = [unit_name for _, unit_name in units]
                
                # 检查对应情况
                print("   购买单位对应情况:")
                for unit in sorted(excel_units)[:10]:
                    if unit in db_unit_names:
                        print(f"     ✅ {unit}: 数据库中存在")
                    else:
                        print(f"     ❌ {unit}: 数据库中不存在")
                
                print()
                
                # 4. 分析具体购买单位的产品对应问题
                print("4. 产品对应问题分析:")
                
                # 分析蕊芯家私1
                if '蕊芯家私1' in excel_units:
                    ruixin_excel = df[df['购买单位'] == '蕊芯家私1']
                    print(f"   蕊芯家私1:")
                    print(f"     Excel产品数: {len(ruixin_excel)}")
                    print(f"     Excel型号示例: {list(ruixin_excel['产品型号'].dropna().head(5))}")
                    
                    # 检查数据库中蕊芯家私1的产品
                    for unit_id, unit_name in units:
                        if unit_name == '蕊芯家私1':
                            cursor.execute('''
                                SELECT p.model_number, p.name
                                FROM products p
                                JOIN customer_products cp ON p.id = cp.product_id
                                WHERE cp.unit_id = ? AND cp.is_active = 1
                                LIMIT 5
                            ''', (unit_id,))
                            db_products = cursor.fetchall()
                            
                            if db_products:
                                print(f"     数据库产品示例:")
                                for model, name in db_products:
                                    print(f"       {model}: {name}")
                            else:
                                print(f"     数据库中无对应产品")
                            break
                    else:
                        print(f"     数据库中无蕊芯家私1")
                
                print()
                
                # 分析其他购买单位
                sample_units = ['七彩乐园', '澜宇']
                for unit in sample_units:
                    if unit in excel_units:
                        unit_excel = df[df['购买单位'] == unit]
                        print(f"   {unit}:")
                        print(f"     Excel产品数: {len(unit_excel)}")
                        print(f"     Excel型号示例: {list(unit_excel['产品型号'].dropna().head(3))}")
                        
                        # 检查数据库中对应
                        for unit_id, unit_name in units:
                            if unit_name == unit:
                                cursor.execute('''
                                    SELECT p.model_number
                                    FROM products p
                                    JOIN customer_products cp ON p.id = cp.product_id
                                    WHERE cp.unit_id = ? AND cp.is_active = 1
                                    LIMIT 3
                                ''', (unit_id,))
                                db_models = cursor.fetchall()
                                
                                if db_models:
                                    print(f"     数据库型号示例: {[model[0] for model in db_models]}")
                                else:
                                    print(f"     数据库中无对应产品")
                                break
                        else:
                            print(f"     数据库中无此购买单位")
                        print()
                
            except Exception as e:
                print(f"   ❌ 分析Excel失败: {e}")
        else:
            print(f"   ❌ Excel文件不存在: {excel_path}")
        
        # 5. 分析数据隔离问题
        print("5. 数据隔离分析:")
        
        # 检查是否有产品被多个购买单位共享
        cursor.execute('''
            SELECT p.model_number, COUNT(DISTINCT cp.unit_id) as unit_count
            FROM products p
            JOIN customer_products cp ON p.id = cp.product_id
            WHERE cp.is_active = 1
            GROUP BY p.model_number
            HAVING COUNT(DISTINCT cp.unit_id) > 1
            ORDER BY unit_count DESC
            LIMIT 5
        ''')
        shared_products = cursor.fetchall()
        
        if shared_products:
            print("   被多个购买单位共享的产品:")
            for model, count in shared_products:
                print(f"     {model}: 被 {count} 个购买单位共享")
        else:
            print("   ✅ 没有产品被多个购买单位共享")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")

if __name__ == "__main__":
    simple_unit_analysis()