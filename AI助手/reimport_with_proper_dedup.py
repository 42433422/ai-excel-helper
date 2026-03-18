#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新导入数据，正确处理去重 - 保留表格中最底下的行
"""

import sqlite3
import pandas as pd
import logging
from collections import defaultdict

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

db_path = "products.db"
excel_path = "templates\\新建 XLSX 工作表 (2).xlsx"

def clean_database():
    """清理数据库"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 删除所有表的数据
        cursor.execute("DELETE FROM customer_products")
        cursor.execute("DELETE FROM products")
        cursor.execute("DELETE FROM purchase_units")
        
        # 重置自增计数器
        cursor.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name = 'customer_products'")
        cursor.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name = 'products'")
        cursor.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name = 'purchase_units'")
        
        conn.commit()
        conn.close()
        logger.info("数据库清理完成")
        return True
    except Exception as e:
        logger.error(f"清理数据库失败: {e}")
        return False

def add_all_purchase_units(df):
    """添加所有购买单位"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取Excel中的所有购买单位
        excel_units = df['购买单位'].dropna().unique()
        logger.info(f"发现 {len(excel_units)} 个购买单位")
        
        # 添加所有购买单位
        added_count = 0
        for unit in excel_units:
            cursor.execute("""
                INSERT INTO purchase_units (unit_name, is_active, created_at, updated_at)
                VALUES (?, 1, datetime('now'), datetime('now'))
            """, (unit,))
            added_count += 1
            logger.info(f"添加购买单位: {unit}")
        
        conn.commit()
        conn.close()
        logger.info(f"成功添加 {added_count} 个购买单位")
        return added_count
    except Exception as e:
        logger.error(f"添加购买单位失败: {e}")
        return 0

def process_products_by_unit_proper_dedup(df):
    """按购买单位处理产品，正确去重 - 保留最后一次出现"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 清理数据
        df_clean = df.dropna(subset=['购买单位', '产品型号', '产品名称', '单价']).copy()
        df_clean = df_clean[df_clean['产品型号'] != '']
        df_clean = df_clean[df_clean['产品名称'] != '']
        logger.info(f"清理后数据: {len(df_clean)} 行")
        
        # 按购买单位分组处理
        unit_product_mapping = {}
        
        for unit in df_clean['购买单位'].unique():
            unit_data = df_clean[df_clean['购买单位'] == unit]
            logger.info(f"处理购买单位 '{unit}' 的 {len(unit_data)} 条产品记录")
            
            # 按购买单位分组，按产品名称和型号组合去重，保留最后一次出现
            # 创建组合键：产品名称 + 产品型号
            unit_data_copy = unit_data.copy()
            unit_data_copy['product_key'] = unit_data_copy['产品名称'].astype(str) + '|' + unit_data_copy['产品型号'].astype(str)
            
            # 按产品键分组，保留最后一次出现
            unit_grouped = unit_data_copy.groupby('product_key').tail(1)
            
            unit_products = []
            for _, row in unit_grouped.iterrows():
                unit_products.append({
                    'model': str(row['产品型号']).strip(),
                    'name': str(row['产品名称']).strip(),
                    'price': float(row['单价']) if pd.notna(row['单价']) else 0.0
                })
            
            unit_product_mapping[unit] = unit_products
            logger.info(f"  - 去重后: {len(unit_products)} 个唯一产品")
        
        # 导入所有产品到数据库（避免重复导入）
        all_products = {}
        for unit, products in unit_product_mapping.items():
            for product in products:
                # 使用产品名称+型号作为唯一键
                product_key = product['name'] + '|' + product['model']
                if product_key not in all_products:
                    all_products[product_key] = product
        
        logger.info(f"导入 {len(all_products)} 个唯一产品")
        
        # 插入产品到数据库
        for product in all_products.values():
            cursor.execute("""
                INSERT INTO products (model_number, name, price, is_active, created_at, updated_at)
                VALUES (?, ?, ?, 1, datetime('now'), datetime('now'))
            """, (product['model'], product['name'], product['price']))
        
        conn.commit()
        
        # 为每个单位创建关联
        created_associations = create_unit_associations(conn, unit_product_mapping)
        
        conn.close()
        
        return len(all_products), created_associations, unit_product_mapping
        
    except Exception as e:
        logger.error(f"处理产品失败: {e}")
        return 0, 0, {}

def create_unit_associations(conn, unit_product_mapping):
    """为每个单位创建产品关联"""
    try:
        cursor = conn.cursor()
        
        # 获取所有产品和购买单位的ID映射
        cursor.execute("SELECT id, model_number, name FROM products WHERE is_active = 1")
        product_id_map = {}
        for row in cursor.fetchall():
            product_key = row[2] + '|' + row[1]  # name + model_number
            product_id_map[product_key] = row[0]
        
        cursor.execute("SELECT id, unit_name FROM purchase_units WHERE is_active = 1")
        unit_id_map = {row[1]: row[0] for row in cursor.fetchall()}
        
        association_count = 0
        
        for unit, products in unit_product_mapping.items():
            unit_id = unit_id_map.get(unit)
            if not unit_id:
                logger.warning(f"找不到购买单位ID: {unit}")
                continue
            
            for product in products:
                product_key = product['name'] + '|' + product['model']
                product_id = product_id_map.get(product_key)
                if not product_id:
                    logger.warning(f"找不到产品ID: {product_key}")
                    continue
                
                cursor.execute("""
                    INSERT INTO customer_products (unit_id, product_id, custom_price, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, 1, datetime('now'), datetime('now'))
                """, (unit_id, product_id, product['price']))
                association_count += 1
        
        conn.commit()
        logger.info(f"创建了 {association_count} 个产品关联")
        return association_count
        
    except Exception as e:
        logger.error(f"创建关联失败: {e}")
        return 0

def verify_import(unit_product_mapping):
    """验证导入结果"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查各购买单位的产品数量
        cursor.execute("""
            SELECT pu.unit_name, COUNT(cp.id) as product_count
            FROM purchase_units pu
            LEFT JOIN customer_products cp ON pu.id = cp.unit_id AND cp.is_active = 1
            WHERE pu.is_active = 1
            GROUP BY pu.id, pu.unit_name
            ORDER BY product_count DESC
        """)
        
        results = cursor.fetchall()
        logger.info("各购买单位产品数量:")
        for unit_name, count in results:
            expected_count = len(unit_product_mapping.get(unit_name, []))
            logger.info(f"  - {unit_name}: {count} 个产品 (期望: {expected_count})")
        
        # 检查蕊芯家私的产品示例
        cursor.execute("""
            SELECT pu.unit_name, p.model_number, p.name, cp.custom_price
            FROM customer_products cp
            JOIN products p ON cp.product_id = p.id
            JOIN purchase_units pu ON cp.unit_id = pu.id
            WHERE pu.unit_name LIKE '%蕊芯%'
            ORDER BY pu.unit_name, p.model_number
            LIMIT 10
        """)
        
        ruixin_products = cursor.fetchall()
        logger.info("蕊芯家私产品示例:")
        for unit_name, model, name, price in ruixin_products:
            logger.info(f"  - {unit_name}: {model} - {name} - ¥{price}")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"验证失败: {e}")
        return False

def main():
    """主函数"""
    print("=== 重新导入数据，正确处理去重 ===")
    
    # 1. 清理数据库
    if clean_database():
        # 2. 读取Excel数据
        df = pd.read_excel(excel_path, sheet_name='Sheet1')
        logger.info(f"读取Excel数据成功，共 {len(df)} 行")
        
        # 3. 添加所有购买单位
        added_units = add_all_purchase_units(df)
        
        # 4. 按单位处理产品（正确去重）
        imported_products, created_associations, unit_product_mapping = process_products_by_unit_proper_dedup(df)
        
        # 5. 验证结果
        if imported_products > 0:
            verify_import(unit_product_mapping)
            
            print(f"\n✅ 重新导入完成！")
            print(f"购买单位: {added_units} 个")
            print(f"产品: {imported_products} 个")
            print(f"关联: {created_associations} 个")
            print(f"\n各购买单位产品数量:")
            for unit, products in unit_product_mapping.items():
                print(f"  - {unit}: {len(products)} 个产品")
            return True
        else:
            print("\n❌ 导入失败！")
            return False
    else:
        print("\n❌ 清理失败！")
        return False

if __name__ == "__main__":
    main()
