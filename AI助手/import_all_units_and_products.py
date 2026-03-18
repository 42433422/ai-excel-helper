#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从新Excel文件导入所有购买单位和产品数据
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

def add_missing_purchase_units():
    """添加缺失的购买单位"""
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

def import_all_products():
    """导入所有产品数据"""
    try:
        # 读取Excel数据
        df = pd.read_excel(excel_path, sheet_name='Sheet1')
        logger.info(f"读取Excel数据成功，共 {len(df)} 行")
        
        # 清理数据：去除空值和无效记录
        df = df.dropna(subset=['产品型号', '产品名称', '单价'])
        df = df[df['产品型号'] != '']
        df = df[df['产品名称'] != '']
        logger.info(f"清理后数据: {len(df)} 行")
        
        # 按产品型号去重，保留最后一次出现的记录
        df_unique = df.drop_duplicates(subset=['产品型号'], keep='last')
        logger.info(f"去重后产品数量: {len(df_unique)}")
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 清理现有产品
        cursor.execute("DELETE FROM customer_products")
        cursor.execute("DELETE FROM products")
        cursor.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name = 'products'")
        cursor.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name = 'customer_products'")
        logger.info("清理了现有产品和关联数据")
        
        # 导入产品
        imported_count = 0
        for _, row in df_unique.iterrows():
            model_number = str(row['产品型号']).strip()
            name = str(row['产品名称']).strip()
            price = float(row['单价']) if pd.notna(row['单价']) else 0.0
            
            # 确保数据有效
            if model_number and name and model_number != 'nan' and name != 'nan':
                cursor.execute("""
                    INSERT INTO products (model_number, name, price, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, 1, datetime('now'), datetime('now'))
                """, (model_number, name, price))
                imported_count += 1
                
                if imported_count <= 10:  # 只打印前10个作为示例
                    logger.info(f"导入产品: {model_number} - {name} (价格: {price})")
                elif imported_count == 11:
                    logger.info("... (更多产品)")
        
        conn.commit()
        conn.close()
        
        logger.info(f"成功导入 {imported_count} 个产品")
        return imported_count
    except Exception as e:
        logger.error(f"导入产品失败: {e}")
        return 0

def recreate_all_customer_products():
    """为所有购买单位创建产品关联"""
    try:
        # 读取Excel数据
        df = pd.read_excel(excel_path, sheet_name='Sheet1')
        
        # 创建产品型号到价格的映射（使用最后一次出现的价格）
        model_price_map = {}
        for _, row in df.iterrows():
            model_number = str(row['产品型号']).strip()
            price = float(row['单价']) if pd.notna(row['单价']) else 0.0
            if model_number and model_number != 'nan':
                model_price_map[model_number] = price
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取所有购买单位
        cursor.execute("SELECT id, unit_name FROM purchase_units WHERE is_active = 1")
        units = cursor.fetchall()
        logger.info(f"找到 {len(units)} 个购买单位")
        
        # 获取所有产品
        cursor.execute("SELECT id, model_number FROM products WHERE is_active = 1")
        products = cursor.fetchall()
        logger.info(f"找到 {len(products)} 个产品")
        
        # 为每个购买单位关联所有产品
        association_count = 0
        for unit in units:
            unit_id = unit[0]
            unit_name = unit[1]
            
            for product in products:
                product_id = product[0]
                model_number = product[1]
                
                # 获取该产品的价格
                price = model_price_map.get(model_number, 0.0)
                
                # 插入关联
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
        
        # 显示前10个购买单位
        cursor.execute("SELECT unit_name FROM purchase_units WHERE is_active = 1 LIMIT 10")
        units = cursor.fetchall()
        logger.info("前10个购买单位:")
        for unit in units:
            logger.info(f"  - {unit[0]}")
        
        # 显示前10个产品
        cursor.execute("SELECT model_number, name FROM products WHERE is_active = 1 LIMIT 10")
        products = cursor.fetchall()
        logger.info("前10个产品:")
        for product in products:
            logger.info(f"  - {product[0]}: {product[1]}")
        
        conn.close()
        
        return {
            'unit_count': unit_count,
            'product_count': product_count,
            'association_count': association_count
        }
    except Exception as e:
        logger.error(f"验证导入失败: {e}")
        return None

def main():
    """主函数"""
    print("=== 从新Excel文件导入所有购买单位和产品 ===")
    
    # 1. 添加缺失的购买单位
    added_units = add_missing_purchase_units()
    if added_units > 0:
        logger.info(f"添加了 {added_units} 个购买单位")
    
    # 2. 导入所有产品
    imported_products = import_all_products()
    if imported_products > 0:
        logger.info(f"导入了 {imported_products} 个产品")
    
    # 3. 重新创建所有关联
    created_associations = recreate_all_customer_products()
    if created_associations > 0:
        logger.info(f"创建了 {created_associations} 个关联")
    
    # 4. 验证导入结果
    result = verify_import()
    if result:
        print(f"\n✅ 导入完成！")
        print(f"购买单位: {result['unit_count']} 个")
        print(f"产品: {result['product_count']} 个")
        print(f"关联: {result['association_count']} 个")
        return True
    
    print("\n❌ 导入失败！")
    return False

if __name__ == "__main__":
    main()
