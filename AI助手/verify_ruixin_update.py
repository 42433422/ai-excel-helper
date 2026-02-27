#!/usr/bin/env python3
# 验证蕊芯家私1更新后的数据

import sqlite3
import os

def verify_ruixin_update():
    """验证蕊芯家私1更新后的数据"""
    print("=== 验证蕊芯家私1更新后的数据 ===")
    
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
            return False
        
        unit_id = result[0]
        print(f"蕊芯家私1的购买单位ID: {unit_id}")
        print()
        
        # 验证专属价格数据
        print("1. 蕊芯家私1的专属价格产品:")
        cursor.execute("""
            SELECT 
                p.model_number, 
                p.name, 
                p.price as general_price,
                cp.custom_price
            FROM products p
            JOIN customer_products cp ON p.id = cp.product_id
            WHERE cp.unit_id = ? AND cp.is_active = 1
            ORDER BY p.model_number
        """, (unit_id,))
        
        products = cursor.fetchall()
        print(f"专属价格产品数量: {len(products)}")
        print()
        
        if products:
            print(f"{'型号':<15} {'产品名称':<25} {'通用价':<8} {'专属价':<8} {'状态'}")
            print("-" * 70)
            
            for model, name, general_price, custom_price in products:
                status = "✅ 使用专属价" if custom_price != general_price else "⚠️ 同价"
                print(f"{model:<15} {name:<25} {general_price:<8.1f} {custom_price:<8.1f} {status}")
        else:
            print("❌ 没有专属价格产品")
        
        print()
        
        # 检查价格重复问题
        print("2. 检查价格重复情况:")
        cursor.execute("""
            SELECT 
                p.model_number,
                COUNT(*) as price_count,
                GROUP_CONCAT(DISTINCT CAST(cp.custom_price AS TEXT)) as prices
            FROM products p
            JOIN customer_products cp ON p.id = cp.product_id
            WHERE cp.unit_id = ? AND cp.is_active = 1
            GROUP BY p.model_number
            HAVING COUNT(*) > 1
        """, (unit_id,))
        
        duplicates = cursor.fetchall()
        
        if duplicates:
            print("❌ 发现重复价格:")
            for model, count, prices in duplicates:
                print(f"  {model}: {count}个价格 - {prices}")
        else:
            print("✅ 没有发现重复价格")
        
        print()
        
        # 测试几个关键产品的价格
        print("3. 关键产品价格测试:")
        test_models = ['9806', '6824A', '24-4-8*', '5020#']
        
        for model in test_models:
            cursor.execute("""
                SELECT 
                    p.name,
                    p.price as general_price,
                    cp.custom_price
                FROM products p
                JOIN customer_products cp ON p.id = cp.product_id
                WHERE cp.unit_id = ? AND p.model_number = ? AND cp.is_active = 1
            """, (unit_id, model))
            
            result = cursor.fetchone()
            
            if result:
                name, general_price, custom_price = result
                print(f"  {model} ({name}):")
                print(f"    通用价: {general_price}元")
                print(f"    专属价: {custom_price}元")
                print(f"    节省: {general_price - custom_price:.1f}元")
            else:
                print(f"  ❌ 未找到产品 {model}")
        
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False

if __name__ == "__main__":
    verify_ruixin_update()