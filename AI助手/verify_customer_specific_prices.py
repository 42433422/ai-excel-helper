#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证AI解析器是否使用客户专属价格
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def verify_customer_specific_prices():
    """验证AI解析器是否使用客户专属价格"""
    
    print("=" * 80)
    print("🔍 验证AI解析器是否使用客户专属价格")
    print("=" * 80)
    
    import sqlite3
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()
    
    print("📊 数据库中的价格对比：")
    print("-" * 60)
    
    # 检查蕊芯家私1（ID=50）的专属产品价格
    print("🔍 蕊芯家私1（客户ID=50）的专属产品价格：")
    cursor.execute("""
        SELECT p.model_number, p.name, p.price as base_price, cp.custom_price as customer_price
        FROM products p 
        JOIN customer_products cp ON p.id = cp.product_id 
        WHERE cp.unit_id = 50 AND p.model_number IN ('9806', '9806A')
        ORDER BY p.model_number
    """)
    
    ruixin_prices = cursor.fetchall()
    for product in ruixin_prices:
        model, name, base_price, customer_price = product
        print(f"  {model} {name}")
        print(f"    基础价格: ¥{base_price}")
        print(f"    客户专属价格: ¥{customer_price}")
        print(f"    价格差异: ¥{customer_price - base_price:.1f}")
        print()
    
    # 检查蕊芯家私（ID=49）的专属产品价格（对比）
    print("🔍 蕊芯家私（客户ID=49）的专属产品价格（对比）：")
    cursor.execute("""
        SELECT p.model_number, p.name, p.price as base_price, cp.custom_price as customer_price
        FROM products p 
        JOIN customer_products cp ON p.id = cp.product_id 
        WHERE cp.unit_id = 49 AND p.model_number IN ('9806', '9806A')
        ORDER BY p.model_number
    """)
    
    ruixin_prices_49 = cursor.fetchall()
    for product in ruixin_prices_49:
        model, name, base_price, customer_price = product
        print(f"  {model} {name}")
        print(f"    基础价格: ¥{base_price}")
        print(f"    客户专属价格: ¥{customer_price}")
        print(f"    价格差异: ¥{customer_price - base_price:.1f}")
        print()
    
    conn.close()
    
    print("=" * 60)
    print("🤖 测试AI解析器的价格获取：")
    print("-" * 60)
    
    from ai_augmented_parser import AIAugmentedShipmentParser
    ai_parser = AIAugmentedShipmentParser()
    
    test_order = "蕊芯1Pe白底漆10桶，规格28KGPE稀释剂:1桶，规格180KG"
    
    try:
        result = ai_parser.parse(test_order)
        
        print(f"订单: {test_order}")
        print(f"客户: {result.purchase_unit}")
        print(f"\n📦 AI解析器获取的价格：")
        
        for i, product in enumerate(result.products, 1):
            model = product['model_number']
            name = product['name']
            ai_price = product['unit_price']
            
            # 查找对应的数据库价格
            for db_product in ruixin_prices:
                if db_product[0] == model:
                    base_price = db_product[2]
                    customer_price = db_product[3]
                    
                    print(f"  产品 {i}: {model} {name}")
                    print(f"    AI解析器价格: ¥{ai_price}")
                    print(f"    数据库基础价格: ¥{base_price}")
                    print(f"    数据库客户专属价格: ¥{customer_price}")
                    
                    if abs(ai_price - customer_price) < 0.01:
                        print(f"    ✅ 确认使用客户专属价格")
                    elif abs(ai_price - base_price) < 0.01:
                        print(f"    ❌ 使用了基础价格（错误）")
                    else:
                        print(f"    ❓ 价格不匹配（需要检查）")
                    break
            print()
        
        # 验证总金额计算
        total_amount = sum(p['amount'] for p in result.products)
        print(f"💰 总金额验证：")
        print(f"  AI计算的总金额: ¥{total_amount}")
        
        # 手动计算正确的总金额
        correct_total = 0
        for product in ruixin_prices:
            model = product[0]
            customer_price = product[3]
            
            # 根据模型计算数量
            if model == '9806':  # PE白底漆
                correct_total += 280 * customer_price  # 280kg
            elif model == '9806A':  # PE稀释剂
                correct_total += 180 * customer_price  # 180kg
        
        print(f"  正确的总金额: ¥{correct_total}")
        
        if abs(total_amount - correct_total) < 0.01:
            print(f"  ✅ 总金额计算正确")
        else:
            print(f"  ❌ 总金额计算错误")
        
    except Exception as e:
        print(f"AI解析测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_customer_specific_prices()