#!/usr/bin/env python3
# 分析数据库问题和数据映射问题

import sqlite3
import pandas as pd
import os

def analyze_database_issues():
    """分析数据库问题"""
    print("=== 分析数据库问题 ===")
    
    try:
        # 连接数据库
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, 'products.db')
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 分析产品重复问题
        print("1. 产品重复问题分析:")
        
        # 按产品名称分组，计算重复次数
        cursor.execute("""
            SELECT 
                name, 
                COUNT(*) as duplicate_count
            FROM products 
            WHERE is_active = 1
            GROUP BY name 
            HAVING COUNT(*) > 1
            ORDER BY duplicate_count DESC
            LIMIT 10
        """)
        
        duplicate_names = cursor.fetchall()
        
        if duplicate_names:
            print("  产品名称重复 Top 10:")
            print(f"  {'产品名称':<20} {'重复次数'}")
            print("  " + "-" * 30)
            for name, count in duplicate_names:
                print(f"  {name:<20} {count}")
        else:
            print("  ✅ 没有产品名称重复")
        
        # 按型号分组，计算重复次数
        cursor.execute("""
            SELECT 
                model_number, 
                COUNT(*) as duplicate_count
            FROM products 
            WHERE is_active = 1 AND model_number != ''
            GROUP BY model_number 
            HAVING COUNT(*) > 1
            ORDER BY duplicate_count DESC
            LIMIT 10
        """)
        
        duplicate_models = cursor.fetchall()
        
        if duplicate_models:
            print("\n  产品型号重复 Top 10:")
            print(f"  {'产品型号':<15} {'重复次数'}")
            print("  " + "-" * 25)
            for model, count in duplicate_models:
                print(f"  {model:<15} {count}")
        else:
            print("\n  ✅ 没有产品型号重复")
        
        print()
        
        # 2. 分析数据结构问题
        print("2. 数据结构问题分析:")
        
        # 检查专属产品 vs 客户专属价
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN purchase_unit_id IS NOT NULL THEN 1 END) as exclusive_products,
                COUNT(CASE WHEN purchase_unit_id IS NULL THEN 1 END) as general_products
            FROM products
            WHERE is_active = 1
        """)
        
        structure = cursor.fetchone()
        if structure:
            exclusive_products, general_products = structure
            total_products = exclusive_products + general_products
            
            print(f"  总产品数: {total_products}")
            print(f"  专属产品: {exclusive_products} ({exclusive_products/total_products*100:.1f}%)")
            print(f"  通用产品: {general_products} ({general_products/total_products*100:.1f}%)")
        
        # 检查客户专属价数量
        cursor.execute("SELECT COUNT(*) FROM customer_products WHERE is_active = 1")
        custom_price_count = cursor.fetchone()[0]
        print(f"  客户专属价: {custom_price_count}")
        
        print()
        
        # 3. 分析数据映射问题
        print("3. 数据映射问题分析:")
        
        # 检查Excel文件
        excel_path = "c:\\Users\\97088\\Desktop\\新建文件夹 (4)\\AI助手\\templates\\新建 XLSX 工作表 (2).xlsx"
        
        if os.path.exists(excel_path):
            try:
                df = pd.read_excel(excel_path, sheet_name='Sheet1')
                print(f"  Excel数据行数: {len(df)}")
                print(f"  Excel列名: {list(df.columns)}")
                
                # 分析不同购买单位的数据量
                unit_counts = df['购买单位'].value_counts()
                print("\n  各购买单位数据量:")
                for unit, count in unit_counts.head(10).items():
                    print(f"    {unit}: {count}条")
                
                # 分析数据格式问题
                print("\n  数据格式分析:")
                print(f"  产品型号空值: {df['产品型号'].isnull().sum()}")
                print(f"  产品名称空值: {df['产品名称'].isnull().sum()}")
                print(f"  单价空值: {df['单价'].isnull().sum()}")
                
            except Exception as e:
                print(f"  ❌ 分析Excel失败: {e}")
        else:
            print(f"  ❌ Excel文件不存在: {excel_path}")
        
        print()
        
        # 4. 分析数据质量问题
        print("4. 数据质量问题分析:")
        
        # 检查价格异常
        cursor.execute("""
            SELECT model_number, name, price
            FROM products
            WHERE is_active = 1 AND price <= 0
        """)
        zero_prices = cursor.fetchall()
        
        if zero_prices:
            print(f"  价格为0或负数的产品: {len(zero_prices)}个")
        else:
            print("  ✅ 没有价格为0或负数的产品")
        
        # 检查产品名称异常
        cursor.execute("""
            SELECT name, COUNT(*)
            FROM products
            WHERE is_active = 1 AND (name IS NULL OR name = '' OR name = 'nan')
            GROUP BY name
        """)
        empty_names = cursor.fetchall()
        
        if empty_names:
            print(f"  产品名称为空的产品: {len(empty_names)}个")
        else:
            print("  ✅ 没有产品名称为空的产品")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")

if __name__ == "__main__":
    analyze_database_issues()