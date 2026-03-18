#!/usr/bin/env python3
# 检查博旺客户的产品信息

import sqlite3
import os

def check_bowang_products():
    """检查博旺客户的产品信息"""
    print("=== 检查博旺客户的产品信息 ===")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'products.db')
    
    print(f"数据库路径: {db_path}")
    print()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 检查是否有博旺这个客户
        print("1. 检查博旺客户:")
        cursor.execute("""
            SELECT id, name FROM customers 
            WHERE name LIKE '%博旺%'
        """)
        bowang_customers = cursor.fetchall()
        
        if bowang_customers:
            print("找到博旺相关客户:")
            for customer in bowang_customers:
                print(f"  ID: {customer[0]}, 名称: {customer[1]}")
            bowang_id = bowang_customers[0][0]
            print()
        else:
            print("❌ 未找到博旺客户")
            # 检查所有客户名称
            cursor.execute("SELECT id, name FROM customers ORDER BY name")
            all_customers = cursor.fetchall()
            print("所有客户列表:")
            for customer in all_customers[:10]:  # 只显示前10个
                print(f"  ID: {customer[0]}, 名称: {customer[1]}")
            if len(all_customers) > 10:
                print(f"  ... 还有 {len(all_customers) - 10} 个客户")
            bowang_id = None
            print()
        
        # 2. 检查S12-19(3#)这个产品的归属
        print("2. 检查S12-19(3#)产品的归属:")
        cursor.execute("""
            SELECT p.id, p.model_number, p.name, p.purchase_unit_id
            FROM products p
            WHERE p.model_number LIKE '%S12-19%'
        """)
        products = cursor.fetchall()
        
        if products:
            for product in products:
                print(f"  产品ID: {product[0]}, 型号: {product[1]}, 名称: {product[2]}, 购买单位ID: {product[3]}")
                
                # 如果有购买单位ID，查看客户信息
                if product[3]:
                    cursor.execute("""
                        SELECT unit_name FROM purchase_units WHERE id = ?
                    """, (product[3],))
                    unit_result = cursor.fetchone()
                    if unit_result:
                        print(f"    归属购买单位: {unit_result[0]}")
            print()
        else:
            print("❌ 未找到S12-19(3#)产品")
            print()
        
        # 3. 检查是否有包含"米白色"的产品
        print("3. 检查包含'米白色'的产品:")
        cursor.execute("""
            SELECT p.id, p.model_number, p.name, p.purchase_unit_id
            FROM products p
            WHERE p.name LIKE '%米白色%' OR p.name LIKE '%米白%'
        """)
        white_products = cursor.fetchall()
        
        if white_products:
            for product in white_products[:10]:  # 只显示前10个
                print(f"  产品ID: {product[0]}, 型号: {product[1]}, 名称: {product[2]}, 购买单位ID: {product[3]}")
                
                # 如果有购买单位ID，查看客户信息
                if product[3]:
                    cursor.execute("""
                        SELECT unit_name FROM purchase_units WHERE id = ?
                    """, (product[3],))
                    unit_result = cursor.fetchone()
                    if unit_result:
                        print(f"    归属购买单位: {unit_result[0]}")
            print()
        else:
            print("❌ 未找到包含'米白色'的产品")
            print()
        
        # 4. 检查所有购买单位
        print("4. 所有购买单位:")
        cursor.execute("""
            SELECT pu.id, pu.unit_name, c.name as customer_name
            FROM purchase_units pu
            LEFT JOIN customers c ON pu.customer_id = c.id
            ORDER BY pu.unit_name
        """)
        units = cursor.fetchall()
        
        print("购买单位列表:")
        for unit in units:
            print(f"  ID: {unit[0]}, 单位名称: {unit[1]}, 客户名称: {unit[2] or 'N/A'}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 数据库查询错误: {e}")

if __name__ == "__main__":
    check_bowang_products()