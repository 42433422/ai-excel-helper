#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按购买单位正确导入产品，每个单位只显示自己的产品
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

def add_new_purchase_units():
    """只添加新的购买单位，不删除现有单位"""
    try:
        # 读取Excel数据
        df = pd.read_excel(excel_path, sheet_name='Sheet1')
        logger.info(f"读取Excel数据成功，共 {len(df)} 行")
        
        # 获取Excel中的所有购买单位
        excel_units = df['购买单位'].dropna().unique()
        logger.info(f"Excel中发现 {len(excel_units)} 个购买单位")
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取数据库中现有的购买单位
        cursor.execute("SELECT unit_name FROM purchase_units WHERE is_active = 1")
        existing_units = [row[0] for row in cursor.fetchall()]
        
        # 找出缺失的购买单位
        missing_units = []
        for unit in excel_units:
            if unit not in existing_units:
                missing_units.append(unit)
        
        logger.info(f"缺失的购买单位 {len(missing_units)} 个:")
        for unit in missing_units:
            logger.info(f"  - {unit}")
        
        # 添加缺失的购买单位
        added_count = 0
        for unit in missing_units:
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

def import_products_by_unit():
    """按购买单位导入产品，不删除现有产品"""
    try:
        # 读取Excel数据
        df = pd.read_excel(excel_path, sheet_name='Sheet1')
        logger.info(f"读取Excel数据成功，共 {len(df)} 行")
        
        # 清理数据：去除空值和无效记录
        df = df.dropna(subset=['购买单位', '产品型号', '产品名称', '单价'])
        df = df[df['产品型号'] != '']
        df = df[df['产品名称'] != '']
        logger.info(f"清理后数据: {len(df)} 行")
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取所有现有的产品（用于检查是否重复）
        cursor.execute("SELECT model_number FROM products WHERE is_active = 1")
        existing_products = set(row[0] for row in cursor.fetchall())
        logger.info(f"现有产品数量: {len(existing_products)}")
        
        # 按购买单位分组，为每个单位导入它的产品
        unit_products = defaultdict(list)
        for _, row in df.iterrows():
            unit = row['购买单位']
            model = row['产品型号']
            name = row['产品名称']
            price = float(row['单价']) if pd.notna(row['单价']) else 0.0
            
            if unit and model and name:
                unit_products[unit].append({
                    'model': str(model).strip(),
                    'name': str(name).strip(),
                    'price': price
                })
        
        # 为每个购买单位导入产品
        imported_by_unit = {}
        for unit, products in unit_products.items():
            logger.info(f"为购买单位 '{unit}' 导入 {len(products)} 个产品")
            
            # 去重该单位的产品（保留最后一次出现）
            unit_unique = {}
            for product in products:
                model = product['model']
                unit_unique[model] = product  # 最后一次出现覆盖前面的
            
            unit_products_unique = list(unit_unique.values())
            imported_by_unit[unit] = len(unit_products_unique)
            
            for product in unit_products_unique:
                model = product['model']
                name = product['name']
                price = product['price']
                
                # 检查产品是否已存在
                if model not in existing_products:
                    cursor.execute("""
                        INSERT INTO products (model_number, name, price, is_active, created_at, updated_at)
                        VALUES (?, ?, ?, 1, datetime('now'), datetime('now'))
                    """, (model, name, price))
                    existing_products.add(model)
                    logger.debug(f"添加新产品: {model} - {name}")
        
        conn.commit()
        conn.close()
        
        logger.info("按单位导入产品完成")
        return imported_by_unit
    except Exception as e:
        logger.error(f"按单位导入产品失败: {e}")
        return {}

def recreate_customer_products_by_unit():
    """为每个购买单位创建只关联其自己产品的关联"""
    try:
        # 读取Excel数据来获取单位-产品映射
        df = pd.read_excel(excel_path, sheet_name='Sheet1')
        df = df.dropna(subset=['购买单位', '产品型号'])
        
        # 创建单位-产品型号映射
        unit_product_models = defaultdict(set)
        for _, row in df.iterrows():
            unit = row['购买单位']
            model = str(row['产品型号']).strip()
            if unit and model:
                unit_product_models[unit].add(model)
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 清理现有关联
        cursor.execute("DELETE FROM customer_products")
        logger.info("清理了现有关联数据")
        
        # 获取所有购买单位
        cursor.execute("SELECT id, unit_name FROM purchase_units WHERE is_active = 1")
        units = cursor.fetchall()
        
        # 获取所有产品
        cursor.execute("SELECT id, model_number FROM products WHERE is_active = 1")
        products = {row[1]: row[0] for row in cursor.fetchall()}
        
        # 为每个购买单位只关联它的产品
        association_count = 0
        for unit in units:
            unit_id = unit[0]
            unit_name = unit[1]
            unit_model_numbers = unit_product_models.get(unit_name, set())
            
            for model in unit_model_numbers:
                if model in products:
                    product_id = products[model]
                    
                    # 获取该产品的价格
                    df_unit = df[(df['购买单位'] == unit_name) & (df['产品型号'].str.strip() == model)]
                    if not df_unit.empty:
                        price = float(df_unit['单价'].iloc[-1]) if pd.notna(df_unit['单价'].iloc[-1]) else 0.0
                        
                        cursor.execute("""
                            INSERT INTO customer_products (unit_id, product_id, custom_price, is_active, created_at, updated_at)
                            VALUES (?, ?, ?, 1, datetime('now'), datetime('now'))
                        """, (unit_id, product_id, price))
                        association_count += 1
        
        conn.commit()
        conn.close()
        
        logger.info(f"成功创建 {association_count} 个产品关联")
        return association_count
    except Exception as e:
        logger.error(f"创建关联失败: {e}")
        return 0

def verify_import():
    """验证导入结果"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查购买单位数量
        cursor.execute("SELECT COUNT(*) FROM purchase_units WHERE is_active = 1")
        unit_count = cursor.fetchone()[0]
        logger.info(f"数据库中购买单位数量: {unit_count}")
        
        # 检查产品数量
        cursor.execute("SELECT COUNT(*) FROM products WHERE is_active = 1")
        product_count = cursor.fetchone()[0]
        logger.info(f"数据库中产品数量: {product_count}")
        
        # 检查关联数量
        cursor.execute("SELECT COUNT(*) FROM customer_products WHERE is_active = 1")
        association_count = cursor.fetchone()[0]
        logger.info(f"数据库中关联数量: {association_count}")
        
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
            logger.info(f"  - {unit_name}: {count} 个产品")
        
        # 检查蕊芯家私的产品
        cursor.execute("""
            SELECT p.model_number, p.name, cp.custom_price
            FROM customer_products cp
            JOIN products p ON cp.product_id = p.id
            JOIN purchase_units pu ON cp.unit_id = pu.id
            WHERE pu.unit_name LIKE '%蕊芯%'
            ORDER BY p.model_number
            LIMIT 5
        """)
        
        ruixin_products = cursor.fetchall()
        logger.info("蕊芯家私前5个产品:")
        for model, name, price in ruixin_products:
            logger.info(f"  - {model}: {name} - ¥{price}")
        
        conn.close()
        
        return {
            'unit_count': unit_count,
            'product_count': product_count,
            'association_count': association_count,
            'unit_product_counts': results
        }
    except Exception as e:
        logger.error(f"验证导入失败: {e}")
        return None

def main():
    """主函数"""
    print("=== 按购买单位正确导入产品 ===")
    
    # 1. 只添加新的购买单位
    added_units = add_new_purchase_units()
    
    # 2. 按单位导入产品（不删除现有产品）
    imported_by_unit = import_products_by_unit()
    
    # 3. 为每个单位只关联其自己的产品
    created_associations = recreate_customer_products_by_unit()
    
    # 4. 验证导入结果
    result = verify_import()
    if result:
        print(f"\n✅ 导入完成！")
        print(f"购买单位: {result['unit_count']} 个")
        print(f"产品: {result['product_count']} 个")
        print(f"关联: {result['association_count']} 个")
        print(f"\n各购买单位产品分布:")
        for unit_name, count in result['unit_product_counts']:
            print(f"  - {unit_name}: {count} 个产品")
        return True
    
    print("\n❌ 导入失败！")
    return False

if __name__ == "__main__":
    main()
