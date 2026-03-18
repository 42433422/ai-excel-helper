#!/usr/bin/env python3
# 检查蕊芯家私1的实际产品情况

import sqlite3
import os

def check_ruixin_products():
    """检查蕊芯家私1的实际产品情况"""
    print("=== 检查蕊芯家私1的实际产品情况 ===")
    
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
        print()
        
        # 查看蕊芯家私1的所有产品
        print("1. 蕊芯家私1的所有专属产品:")
        cursor.execute("""
            SELECT p.id, p.model_number, p.name, p.price
            FROM products p
            WHERE p.purchase_unit_id = ?
            ORDER BY p.model_number
        """, (unit_id,))
        
        ruixin_products = cursor.fetchall()
        
        if ruixin_products:
            print(f"  找到 {len(ruixin_products)} 个专属产品:")
            for product in ruixin_products:
                print(f"    ID: {product[0]}, 型号: {product[1]}, 名称: {product[2]}, 价格: {product[3]}, 规格: {product[4]}")
        else:
            print("  ❌ 没有专属产品")
        
        print()
        
        # 查看蕊芯家私1的客户专属产品
        print("2. 蕊芯家私1的客户专属产品:")
        cursor.execute("""
            SELECT cp.id, cp.custom_price, p.model_number, p.name, p.price
            FROM customer_products cp
            JOIN products p ON cp.product_id = p.id
            WHERE cp.unit_id = ?
            ORDER BY p.model_number
        """, (unit_id,))
        
        cp_products = cursor.fetchall()
        
        if cp_products:
            print(f"  找到 {len(cp_products)} 个客户专属产品:")
            for product in cp_products:
                print(f"    记录ID: {product[0]}, 专属价: {product[1]}, 型号: {product[2]}, 名称: {product[3]}, 原价: {product[4]}")
        else:
            print("  ❌ 没有客户专属产品")
        
        print()
        
        # 查看所有购买单位
        print("3. 所有购买单位:")
        cursor.execute("""
            SELECT pu.id, pu.unit_name, c.name as customer_name
            FROM purchase_units pu
            LEFT JOIN customers c ON pu.customer_id = c.id
            ORDER BY pu.id
        """)
        
        all_units = cursor.fetchall()
        
        print("  购买单位列表:")
        for unit in all_units:
            print(f"    ID: {unit[0]}, 单位名称: {unit[1]}, 客户名称: {unit[2] or 'N/A'}")
        
        print()
        
        # 查看所有蕊芯相关的产品（不限定购买单位）
        print("4. 所有包含'蕊芯'或型号匹配的产品:")
        internal_models = ['9806', '9806A', '6824A', 'RX1872', 'RX-GAA', '2501225*', 'RX70F', 'A0061', '9016', '1005', '1007', '24-4-8*', '5020#']
        
        for model in internal_models:
            cursor.execute("""
                SELECT p.id, p.model_number, p.name, p.purchase_unit_id, pu.unit_name
                FROM products p
                LEFT JOIN purchase_units pu ON p.purchase_unit_id = pu.id
                WHERE p.model_number = ?
                LIMIT 1
            """, (model,))
            
            result = cursor.fetchone()
            if result:
                print(f"  找到产品 {model}: ID={result[0]}, 名称={result[2]}, 购买单位={result[4] or '通用'}")
            else:
                print(f"  ❌ 未找到产品 {model}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 数据库查询错误: {e}")

if __name__ == "__main__":
    check_ruixin_products()