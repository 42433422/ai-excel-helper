#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终验证解析器修复
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_database_connection():
    """测试数据库连接和查询"""
    import sqlite3
    
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()
    
    print("=== 数据库连接测试 ===")
    
    # 测试购买单位查询
    try:
        cursor.execute("SELECT id, unit_name FROM purchase_units WHERE unit_name LIKE '%蕊芯%' AND is_active = 1")
        units = cursor.fetchall()
        print(f"✅ 购买单位查询成功: {len(units)}个蕊芯相关客户")
        for unit in units:
            print(f"  - ID {unit[0]}: {unit[1]}")
    except Exception as e:
        print(f"❌ 购买单位查询失败: {e}")
    
    # 测试产品查询
    try:
        cursor.execute("SELECT p.id, p.model_number, p.name, cp.custom_price FROM products p JOIN customer_products cp ON p.id = cp.product_id WHERE cp.unit_id = 50 AND cp.is_active = 1 LIMIT 3")
        products = cursor.fetchall()
        print(f"\n✅ 产品查询成功: {len(products)}个产品")
        for product in products:
            print(f"  - ID {product[0]}: {product[1]} - {product[2]} (¥{product[3]})")
    except Exception as e:
        print(f"\n❌ 产品查询失败: {e}")
    
    conn.close()

def test_shipment_parser():
    """测试发货单解析器"""
    try:
        from shipment_parser import ShipmentParser
        
        # 使用简单的测试订单
        order_text = "蕊芯1需要PE白底漆 10桶"
        
        print(f"\n=== 发货单解析器测试 ===")
        print(f"测试订单: {order_text}")
        
        # 创建解析器实例
        parser = ShipmentParser(db_path="products.db")
        
        # 解析订单
        result = parser.parse(order_text)
        
        print(f"✅ 解析成功!")
        print(f"  客户单位: {result.purchase_unit}")
        print(f"  产品数量: {len(result.products)}")
        
        if result.products:
            for i, product in enumerate(result.products, 1):
                print(f"  产品 {i}: {product.get('name', '未知')} - {product.get('quantity_tins', 0)}桶")
        
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_database_connection()
    test_shipment_parser()