#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复版：从出货记录中提取蕊芯数据并创建购买单位
"""

import pandas as pd
import sqlite3
import os
import re
from collections import defaultdict

def extract_ruixin_products():
    """从出货记录中提取蕊芯产品数据"""
    
    excel_file = "尹玉华1 - 副本.xlsx"
    
    print("=== 从出货记录中提取蕊芯产品数据 ===")
    
    if not os.path.exists(excel_file):
        print(f"❌ 文件不存在: {excel_file}")
        return None
    
    try:
        # 读取Excel文件
        print(f"📖 读取Excel文件: {excel_file}")
        df = pd.read_excel(excel_file)
        
        # 提取蕊芯相关数据
        print("\n🔍 提取蕊芯相关产品数据...")
        
        # 产品价格字典
        product_prices = defaultdict(list)
        
        # 遍历数据
        for index, row in df.iterrows():
            # 检查是否是蕊芯的记录
            customer_name = str(row.get('Unnamed: 0', '')).strip()
            if customer_name != '蕊芯':
                continue
            
            # 获取产品信息
            model = str(row.get('Unnamed: 3', '')).strip()
            product_name = str(row.get('Unnamed: 6', '')).strip()
            price = row.get('金额总计')  # 单价
            customer_price = row.get('客户金额总计')  # 客户单价
            
            # 只处理有型号和价格的数据
            if model and model != 'nan' and price and pd.notna(price):
                # 清理型号
                model = re.sub(r'[^A-Z0-9-]', '', model.upper())
                if model:
                    product_prices[model].append({
                        'price': float(price),
                        'customer_price': float(customer_price) if customer_price and pd.notna(customer_price) else None,
                        'product_name': product_name
                    })
        
        # 计算平均价格
        products = []
        for model, price_data in product_prices.items():
            # 计算平均价格
            avg_price = sum(item['price'] for item in price_data) / len(price_data)
            
            # 计算平均客户价格
            customer_prices = [item['customer_price'] for item in price_data if item['customer_price']]
            avg_customer_price = sum(customer_prices) / len(customer_prices) if customer_prices else avg_price
            
            # 获取最常见的产品名称
            product_names = [item['product_name'] for item in price_data if item['product_name'] and item['product_name'] != 'nan']
            common_name = max(set(product_names), key=product_names.count) if product_names else f"产品_{model}"
            
            products.append({
                'model': model,
                'name': common_name,
                'price_internal': avg_price,       # 内价
                'price_external': avg_customer_price  # 外价
            })
        
        print(f"✅ 提取到 {len(products)} 个产品")
        
        # 显示前10个产品
        print("\n📄 前10个产品数据:")
        for i, product in enumerate(products[:10]):
            print(f"  {i+1}. 型号: {product['model']}, 名称: {product['name']}, 内价: {product['price_internal']:.2f}, 外价: {product['price_external']:.2f}")
        
        return products
        
    except Exception as e:
        print(f"❌ 提取数据失败: {e}")
        return None

def create_tables_if_not_exists():
    """创建表结构（如果不存在）"""
    
    print("\n=== 创建表结构 ===")
    
    conn = sqlite3.connect("products.db")
    cursor = conn.cursor()
    
    try:
        # 创建 products 表（如果不存在）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_number TEXT NOT NULL,
                name TEXT NOT NULL,
                specification TEXT,
                price REAL,
                quantity INTEGER,
                description TEXT,
                category TEXT,
                brand TEXT,
                unit TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                purchase_unit_id INTEGER
            )
        """)
        print("✅ 创建 products 表")
        
        conn.commit()
        print("✅ 表结构创建完成")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 创建表结构失败: {e}")
    finally:
        conn.close()

def create_ruixin_units():
    """创建蕊芯家私购买单位"""
    
    print("\n=== 创建蕊芯家私购买单位 ===")
    
    conn = sqlite3.connect("products.db")
    cursor = conn.cursor()
    
    try:
        # 先清理已存在的蕊芯相关购买单位
        cursor.execute("""
            SELECT id, unit_name FROM purchase_units 
            WHERE unit_name LIKE '%蕊芯%'
        """)
        existing = cursor.fetchall()
        
        if existing:
            print(f"⚠️  清理已存在的蕊芯购买单位: {len(existing)} 个")
            for unit in existing:
                cursor.execute("DELETE FROM purchase_units WHERE id = ?", (unit[0],))
            conn.commit()
        
        # 创建两个购买单位（使用正确的表结构）
        units_to_create = [
            ('蕊芯家私', '刘总', '', '地址', 1),  # 外
            ('蕊芯家私1', '刘总', '', '地址', 1)  # 内
        ]
        
        created_units = []
        for unit_name, contact, phone, address, is_active in units_to_create:
            cursor.execute("""
                INSERT INTO purchase_units 
                (unit_name, contact_person, contact_phone, address, is_active)
                VALUES (?, ?, ?, ?, ?)
            """, (unit_name, contact, phone, address, is_active))
            
            unit_id = cursor.lastrowid
            created_units.append({'id': unit_id, 'name': unit_name})
            print(f"✅ 创建购买单位: {unit_name} (ID: {unit_id})")
        
        conn.commit()
        print(f"\n✅ 成功创建 {len(created_units)} 个购买单位")
        return created_units
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 创建购买单位失败: {e}")
        return []
    finally:
        conn.close()

def import_ruixin_products(products, units):
    """导入蕊芯产品数据"""
    
    print("\n=== 导入蕊芯产品数据 ===")
    
    if not products or not units:
        print("❌ 无数据可导入")
        return
    
    conn = sqlite3.connect("products.db")
    cursor = conn.cursor()
    
    try:
        # 获取购买单位ID
        ruixin_outer = next((u for u in units if u['name'] == '蕊芯家私'), None)
        ruixin_inner = next((u for u in units if u['name'] == '蕊芯家私1'), None)
        
        if not ruixin_outer or not ruixin_inner:
            print("❌ 未找到购买单位")
            return
        
        print(f"📋 购买单位映射:")
        print(f"  蕊芯家私 (外): ID = {ruixin_outer['id']}")
        print(f"  蕊芯家私1 (内): ID = {ruixin_inner['id']}")
        
        # 导入产品
        imported_count = 0
        
        for product in products:
            model = product['model']
            name = product['name']
            price_outer = product['price_external']  # 外价
            price_inner = product['price_internal']  # 内价
            
            # 导入外价（蕊芯家私）
            cursor.execute("""
                INSERT INTO products 
                (model_number, name, price, unit, is_active, purchase_unit_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (model, name, price_outer, 'kg', 1, ruixin_outer['id']))
            imported_count += 1
            
            # 导入内价（蕊芯家私1）
            cursor.execute("""
                INSERT INTO products 
                (model_number, name, price, unit, is_active, purchase_unit_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (model, name, price_inner, 'kg', 1, ruixin_inner['id']))
            imported_count += 1
        
        conn.commit()
        print(f"\n✅ 成功导入 {imported_count} 个产品")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 导入产品失败: {e}")
    finally:
        conn.close()

def verify_import():
    """验证导入结果"""
    
    print("\n=== 验证导入结果 ===")
    
    conn = sqlite3.connect("products.db")
    cursor = conn.cursor()
    
    try:
        # 检查购买单位
        cursor.execute("""
            SELECT id, unit_name, contact_person 
            FROM purchase_units 
            WHERE unit_name LIKE '%蕊芯家私%'
            ORDER BY unit_name
        """)
        units = cursor.fetchall()
        
        print(f"📋 蕊芯家私购买单位:")
        for unit in units:
            print(f"  ID: {unit[0]}, 名称: {unit[1]}, 联系人: {unit[2]}")
            
            # 检查每个购买单位的产品数据
            cursor.execute("""
                SELECT model_number, name, price, unit 
                FROM products 
                WHERE purchase_unit_id = ?
                ORDER BY model_number
                LIMIT 10
            """, (unit[0],))
            products = cursor.fetchall()
            
            if products:
                print(f"    产品数量: {len(products)} 个")
                for product in products[:5]:
                    print(f"      型号: {product[0]}, 名称: {product[1]}, 价格: {product[2]:.2f}, 单位: {product[3]}")
                if len(products) > 5:
                    print(f"      ... 还有 {len(products) - 5} 个产品")
            else:
                print(f"    无产品数据")
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
    finally:
        conn.close()

def main():
    """主函数"""
    
    # 从Excel提取产品数据
    products = extract_ruixin_products()
    if not products:
        print("❌ 无产品数据可处理")
        return
    
    # 创建表结构
    create_tables_if_not_exists()
    
    # 创建购买单位
    units = create_ruixin_units()
    if not units:
        print("❌ 创建购买单位失败")
        return
    
    # 导入产品数据
    import_ruixin_products(products, units)
    
    # 验证导入结果
    verify_import()
    
    print("\n🎉 蕊芯家私数据导入完成！")

if __name__ == "__main__":
    main()