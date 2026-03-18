#!/usr/bin/env python3
# 检查公司产品的独立性和数据完整性

import sqlite3
import os

def check_company_products():
    """检查公司产品的独立性和数据完整性"""
    print("=== 检查公司产品的独立性和数据完整性 ===")
    
    try:
        # 连接数据库
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, 'products.db')
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 检查所有购买单位及其专属产品数量
        print("1. 购买单位及其专属产品统计:")
        cursor.execute("""
            SELECT 
                pu.id,
                pu.unit_name,
                COUNT(CASE WHEN p.purchase_unit_id IS NOT NULL THEN 1 END) as exclusive_products,
                COUNT(CASE WHEN cp.unit_id IS NOT NULL THEN 1 END) as custom_products
            FROM purchase_units pu
            LEFT JOIN products p ON p.purchase_unit_id = pu.id
            LEFT JOIN customer_products cp ON cp.unit_id = pu.id AND cp.is_active = 1
            GROUP BY pu.id, pu.unit_name
            ORDER BY pu.unit_name
        """)
        
        units = cursor.fetchall()
        
        print(f"{'ID':<5} {'单位名称':<15} {'专属产品':<10} {'客户专属产品':<15}")
        print("-" * 50)
        
        for unit in units:
            unit_id, unit_name, exclusive_products, custom_products = unit
            print(f"{unit_id:<5} {unit_name:<15} {exclusive_products:<10} {custom_products:<15}")
        
        print()
        
        # 2. 检查重复的产品名称和型号
        print("2. 检查重复的产品名称和型号:")
        
        # 检查重复的产品名称
        cursor.execute("""
            SELECT name, COUNT(*) as count
            FROM products
            WHERE name IS NOT NULL AND name != ''
            GROUP BY name
            HAVING COUNT(*) > 1
            ORDER BY count DESC
            LIMIT 10
        """)
        
        duplicate_names = cursor.fetchall()
        
        if duplicate_names:
            print("重复的产品名称:")
            for name, count in duplicate_names:
                print(f"  '{name}': {count}次")
        else:
            print("✅ 没有重复的产品名称")
        
        # 检查重复的型号
        cursor.execute("""
            SELECT model_number, COUNT(*) as count
            FROM products
            WHERE model_number IS NOT NULL AND model_number != ''
            GROUP BY model_number
            HAVING COUNT(*) > 1
            ORDER BY count DESC
            LIMIT 10
        """)
        
        duplicate_models = cursor.fetchall()
        
        if duplicate_models:
            print("\n重复的产品型号:")
            for model, count in duplicate_models:
                print(f"  '{model}': {count}次")
        else:
            print("✅ 没有重复的产品型号")
        
        print()
        
        # 3. 检查产品和客户专属产品的关联
        print("3. 检查产品和客户专属产品的关联情况:")
        
        # 统计情况
        cursor.execute("""
            SELECT 
                '通用产品' as type,
                COUNT(*) as count
            FROM products
            WHERE purchase_unit_id IS NULL
            UNION ALL
            SELECT 
                '专属产品' as type,
                COUNT(*) as count
            FROM products
            WHERE purchase_unit_id IS NOT NULL
            UNION ALL
            SELECT 
                '客户专属价' as type,
                COUNT(*) as count
            FROM customer_products
            WHERE is_active = 1
        """)
        
        stats = cursor.fetchall()
        
        for type_name, count in stats:
            print(f"  {type_name}: {count}个")
        
        print()
        
        # 4. 检查蕊芯家私1的具体情况
        print("4. 蕊芯家私1的产品情况:")
        
        ruixin_unit_id = None
        cursor.execute("SELECT id FROM purchase_units WHERE unit_name = ?", ("蕊芯家私1",))
        result = cursor.fetchone()
        if result:
            ruixin_unit_id = result[0]
        
        if ruixin_unit_id:
            # 专属产品
            cursor.execute("""
                SELECT p.model_number, p.name, p.price
                FROM products p
                WHERE p.purchase_unit_id = ?
                ORDER BY p.model_number
            """, (ruixin_unit_id,))
            
            exclusive_products = cursor.fetchall()
            
            if exclusive_products:
                print(f"  专属产品 ({len(exclusive_products)}个):")
                for model, name, price in exclusive_products:
                    print(f"    {model}: {name} - {price}元")
            else:
                print("  专属产品: 无")
            
            # 客户专属价产品
            cursor.execute("""
                SELECT p.model_number, p.name, cp.custom_price
                FROM products p
                JOIN customer_products cp ON p.id = cp.product_id
                WHERE cp.unit_id = ? AND cp.is_active = 1
                ORDER BY p.model_number
            """, (ruixin_unit_id,))
            
            custom_products = cursor.fetchall()
            
            if custom_products:
                print(f"  客户专属价产品 ({len(custom_products)}个):")
                for model, name, price in custom_products:
                    print(f"    {model}: {name} - {price}元")
            else:
                print("  客户专属价产品: 无")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 数据库查询错误: {e}")

if __name__ == "__main__":
    check_company_products()