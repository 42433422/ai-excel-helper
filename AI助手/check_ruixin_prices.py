#!/usr/bin/env python3
# 检查蕊芯家私1的价格优先级逻辑

import sqlite3
import os

def check_ruixin_prices():
    """检查蕊芯家私1的价格优先级逻辑"""
    print("=== 检查蕊芯家私1的价格优先级逻辑 ===")
    
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
        
        # 检查一些有内部价的产品是否有通用价冲突
        test_models = ['9806', '6824A', '24-4-8*', '5020#']
        
        for model in test_models:
            print(f"\n检查产品 {model}:")
            
            # 检查专属价格
            cursor.execute("""
                SELECT p.model_number, p.name, p.price, cp.custom_price
                FROM products p
                LEFT JOIN customer_products cp ON p.id = cp.product_id AND cp.unit_id = ?
                WHERE p.model_number = ?
            """, (unit_id, model))
            
            result = cursor.fetchone()
            
            if result:
                model_number, name, general_price, custom_price = result
                print(f"  产品名称: {name}")
                print(f"  通用价格: {general_price}元")
                print(f"  专属价格: {custom_price}元" if custom_price else "  专属价格: 无")
                
                # 模拟当前逻辑
                if custom_price:
                    current_price = custom_price
                    print(f"  当前逻辑价格: {current_price}元 (使用专属价格)")
                else:
                    current_price = general_price
                    print(f"  当前逻辑价格: {current_price}元 (回退到通用价格)")
            else:
                print(f"  ❌ 未找到产品 {model}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 数据库查询错误: {e}")

if __name__ == "__main__":
    check_ruixin_prices()