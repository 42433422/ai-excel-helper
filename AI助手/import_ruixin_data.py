#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从Excel导入蕊芯家私数据
"""

import pandas as pd
import sqlite3
import os
import re

def analyze_excel_structure():
    """分析Excel文件结构"""
    
    excel_file = "尹玉华1 - 副本.xlsx"
    
    print("=== 分析Excel文件结构 ===")
    
    if not os.path.exists(excel_file):
        print(f"❌ 文件不存在: {excel_file}")
        return None
    
    try:
        # 读取Excel文件
        print(f"📖 读取Excel文件: {excel_file}")
        df = pd.read_excel(excel_file)
        
        print(f"📊 Excel数据形状: {df.shape}")
        print(f"📋 列名: {list(df.columns)}")
        
        # 显示前几行数据
        print("\n📄 前10行数据:")
        print(df.head(10))
        
        # 查找包含"蕊芯"的列
        ruixin_columns = []
        for col in df.columns:
            if '蕊芯' in str(col):
                ruixin_columns.append(col)
        
        print(f"\n🔍 包含'蕊芯'的列: {ruixin_columns}")
        
        return df
        
    except Exception as e:
        print(f"❌ 分析Excel文件失败: {e}")
        return None

def extract_ruixin_data(df):
    """提取蕊芯相关数据"""
    
    print("\n=== 提取蕊芯数据 ===")
    
    # 查找蕊芯相关的列
    ruixin1_col = None  # 蕊芯1（外）
    ruixin_col = None   # 蕊芯（内）
    model_col = None    # 产品型号列
    
    # 遍历列名
    for col in df.columns:
        col_str = str(col)
        if '蕊芯1' in col_str or '蕊芯一' in col_str:
            ruixin1_col = col
            print(f"✅ 找到蕊芯1列: {col_str}")
        elif '蕊芯' in col_str and '蕊芯1' not in col_str:
            ruixin_col = col
            print(f"✅ 找到蕊芯列: {col_str}")
    
    # 查找产品型号列
    for col in df.columns:
        col_str = str(col)
        if '型号' in col_str or '产品型号' in col_str or 'RX' in col_str:
            model_col = col
            print(f"✅ 找到产品型号列: {col_str}")
            break
    
    # 如果没找到，尝试从数据中推断
    if model_col is None:
        # 查找包含RX开头或数字+字母组合的列
        for col in df.columns:
            sample_data = df[col].dropna().head(10)
            rx_count = sum(1 for val in sample_data if re.search(r'^RX|\d+[A-Z]', str(val), re.IGNORECASE))
            if rx_count > 5:
                model_col = col
                print(f"✅ 推断产品型号列: {str(col)}")
                break
    
    if model_col is None:
        print("❌ 未找到产品型号列")
        return None
    
    # 提取产品数据
    print("\n🔍 提取产品数据:")
    products = []
    
    for index, row in df.iterrows():
        # 获取型号
        model = str(row.get(model_col, '')).strip()
        if not model or model == 'nan':
            continue
        
        # 获取价格
        price_ruixin1 = row.get(ruixin1_col, None)
        price_ruixin = row.get(ruixin_col, None)
        
        # 只处理有价格的数据
        if price_ruixin1 is not None and pd.notna(price_ruixin1):
            products.append({
                'model': model,
                'price_ruixin1': float(price_ruixin1),
                'price_ruixin': float(price_ruixin) if price_ruixin is not None and pd.notna(price_ruixin) else None
            })
    
    print(f"✅ 提取到 {len(products)} 个产品")
    
    # 显示前几个产品
    print("\n📄 前5个产品数据:")
    for i, product in enumerate(products[:5]):
        print(f"  {i+1}. 型号: {product['model']}, 蕊芯1价格: {product['price_ruixin1']}, 蕊芯价格: {product['price_ruixin']}")
    
    return products

def create_purchase_units():
    """创建购买单位"""
    
    print("\n=== 创建购买单位 ===")
    
    conn = sqlite3.connect("products.db")
    cursor = conn.cursor()
    
    try:
        # 检查是否已有蕊芯家私相关购买单位
        cursor.execute("""
            SELECT id, unit_name FROM purchase_units 
            WHERE unit_name LIKE '%蕊芯家私%'
        """)
        existing = cursor.fetchall()
        
        if existing:
            print(f"⚠️  已存在 {len(existing)} 个蕊芯家私购买单位:")
            for unit in existing:
                print(f"  ID: {unit[0]}, 名称: {unit[1]}")
                # 删除已存在的
                cursor.execute("DELETE FROM purchase_units WHERE id = ?", (unit[0],))
                print(f"  删除: {unit[1]}")
            conn.commit()
        
        # 创建新的购买单位
        units_to_create = [
            ('蕊芯家私', '刘总', '', 1.0, '外'),  # 蕊芯家私（外）
            ('蕊芯家私1', '刘总', '', 1.0, '内')  # 蕊芯家私1（内）
        ]
        
        created_units = []
        for unit_name, contact, phone, discount, notes in units_to_create:
            cursor.execute("""
                INSERT INTO purchase_units 
                (unit_name, contact_person, contact_phone, discount_rate, notes, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (unit_name, contact, phone, discount, notes, 1))
            
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

def import_products(products, purchase_units):
    """导入产品数据"""
    
    print("\n=== 导入产品数据 ===")
    
    if not products or not purchase_units:
        print("❌ 无数据可导入")
        return
    
    conn = sqlite3.connect("products.db")
    cursor = conn.cursor()
    
    try:
        # 获取购买单位ID
        ruixin_unit = next((u for u in purchase_units if u['name'] == '蕊芯家私'), None)
        ruixin1_unit = next((u for u in purchase_units if u['name'] == '蕊芯家私1'), None)
        
        if not ruixin_unit or not ruixin1_unit:
            print("❌ 未找到购买单位")
            return
        
        print(f"📋 购买单位映射:")
        print(f"  蕊芯家私 (外): ID = {ruixin_unit['id']}")
        print(f"  蕊芯家私1 (内): ID = {ruixin1_unit['id']}")
        
        # 导入产品
        imported_count = 0
        
        for product in products:
            model = product['model']
            
            # 导入蕊芯家私（外）
            if product['price_ruixin1']:
                cursor.execute("""
                    INSERT INTO products 
                    (model_number, name, price, unit, is_active, purchase_unit_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (model, f"产品_{model}", product['price_ruixin1'], '个', 1, ruixin_unit['id']))
                imported_count += 1
            
            # 导入蕊芯家私1（内）
            if product['price_ruixin']:
                cursor.execute("""
                    INSERT INTO products 
                    (model_number, name, price, unit, is_active, purchase_unit_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (model, f"产品_{model}", product['price_ruixin'], '个', 1, ruixin1_unit['id']))
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
            SELECT id, unit_name, contact_person, discount_rate 
            FROM purchase_units 
            WHERE unit_name LIKE '%蕊芯家私%'
            ORDER BY unit_name
        """)
        units = cursor.fetchall()
        
        print(f"📋 蕊芯家私购买单位:")
        for unit in units:
            print(f"  ID: {unit[0]}, 名称: {unit[1]}, 联系人: {unit[2]}, 折扣: {unit[3]}")
            
            # 检查每个购买单位的产品
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
                    print(f"      型号: {product[0]}, 价格: {product[2]}, 单位: {product[3]}")
                if len(products) > 5:
                    print(f"      ... 还有 {len(products) - 5} 个产品")
            else:
                print(f"    无产品")
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
    finally:
        conn.close()

def main():
    """主函数"""
    
    # 分析Excel文件
    df = analyze_excel_structure()
    if df is None:
        return
    
    # 提取蕊芯数据
    products = extract_ruixin_data(df)
    if not products:
        print("❌ 无数据可处理")
        return
    
    # 创建购买单位
    purchase_units = create_purchase_units()
    if not purchase_units:
        print("❌ 创建购买单位失败")
        return
    
    # 导入产品
    import_products(products, purchase_units)
    
    # 验证导入结果
    verify_import()
    
    print("\n🎉 蕊芯家私数据导入完成！")

if __name__ == "__main__":
    main()