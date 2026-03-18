#!/usr/bin/env python3
# 深入调试博旺的解析过程

import sqlite3
import os
from ai_augmented_parser import AIAugmentedShipmentParser

def debug_bowang_parsing():
    """深入调试博旺的解析过程"""
    print("=== 深入调试博旺的解析过程 ===")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'products.db')
    
    # 1. 查看所有包含S12-19的产品
    print("1. 查看所有包含S12-19的产品:")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT p.id, p.model_number, p.name, p.purchase_unit_id, pu.unit_name
            FROM products p
            LEFT JOIN purchase_units pu ON p.purchase_unit_id = pu.id
            WHERE p.model_number LIKE '%S12-19%' OR p.model_number LIKE '%S12-19%'
        """)
        products = cursor.fetchall()
        
        if products:
            for product in products:
                print(f"  产品ID: {product[0]}, 型号: {product[1]}, 名称: {product[2]}")
                print(f"    购买单位ID: {product[3]}, 购买单位名称: {product[4] or 'None'}")
        else:
            print("  ❌ 未找到S12-19产品")
        
        conn.close()
        print()
    except Exception as e:
        print(f"❌ 查询错误: {e}")
    
    # 2. 查看博旺专属产品
    print("2. 查看博旺专属产品:")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT p.id, p.model_number, p.name, p.price
            FROM products p
            WHERE p.purchase_unit_id = 17  -- 博旺家私的ID
            LIMIT 10
        """)
        bowang_products = cursor.fetchall()
        
        if bowang_products:
            print(f"  找到 {len(bowang_products)} 个博旺专属产品:")
            for product in bowang_products:
                print(f"    产品ID: {product[0]}, 型号: {product[1]}, 名称: {product[2]}, 价格: {product[3]}")
        else:
            print("  ❌ 博旺没有专属产品")
        
        conn.close()
        print()
    except Exception as e:
        print(f"❌ 查询错误: {e}")
    
    # 3. 查看客户专属产品
    print("3. 查看customer_products表中的博旺专属产品:")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT cp.id, cp.unit_id, cp.product_id, cp.custom_price, 
                   p.model_number, p.name, pu.unit_name
            FROM customer_products cp
            JOIN products p ON cp.product_id = p.id
            JOIN purchase_units pu ON cp.unit_id = pu.id
            WHERE pu.unit_name LIKE '%博旺%'
            LIMIT 10
        """)
        cp_products = cursor.fetchall()
        
        if cp_products:
            print(f"  找到 {len(cp_products)} 个博旺专属产品记录:")
            for product in cp_products:
                print(f"    记录ID: {product[0]}, 产品ID: {product[2]}")
                print(f"      型号: {product[4]}, 名称: {product[5]}")
                print(f"      专属价格: {product[3]}, 购买单位: {product[6]}")
        else:
            print("  ❌ customer_products表中没有博旺专属产品")
        
        conn.close()
        print()
    except Exception as e:
        print(f"❌ 查询错误: {e}")
    
    # 4. 测试AI解析器的详细过程
    print("4. 测试AI解析器的详细过程:")
    parser = AIAugmentedShipmentParser()
    
    test_text = "博旺，pu哑光米白色漆2桶规格25"
    print(f"  测试文本: '{test_text}'")
    
    # AI提取结果
    ai_result = parser._call_deepseek_for_product_extraction(test_text, number_mode=True)
    
    if ai_result:
        print("  AI提取结果:")
        print(f"    购买单位: {ai_result.get('purchase_unit', 'N/A')}")
        for i, product in enumerate(ai_result.get('products', []), 1):
            print(f"    产品 {i}:")
            print(f"      名称: {product.get('name', 'N/A')}")
            print(f"      型号: {product.get('model_number', 'N/A')}")
    
    print("\n=== 调试完成 ===")

if __name__ == "__main__":
    debug_bowang_parsing()