#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理数据库并重新正确导入Excel文件中的产品
"""

import sqlite3
import pandas as pd
import logging
import os

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

db_path = "products.db"
excel_path = "尹玉华1 - 副本.xlsx"

def clean_database():
    """清理数据库中的产品和关联数据"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 清理customer_products表
        cursor.execute("DELETE FROM customer_products")
        logger.info("清理了customer_products表")
        
        # 清理products表
        cursor.execute("DELETE FROM products")
        logger.info("清理了products表")
        
        # 重置自增计数器
        cursor.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name = 'products'")
        cursor.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name = 'customer_products'")
        
        conn.commit()
        conn.close()
        
        logger.info("数据库清理完成")
        return True
    except Exception as e:
        logger.error(f"清理数据库失败: {e}")
        return False

def import_products_from_excel():
    """从Excel文件导入产品"""
    try:
        # 读取Excel文件，使用第二行作为列标题
        df = pd.read_excel(excel_path, header=1)
        logger.info(f"读取Excel文件成功，共 {len(df)} 行数据")
        
        # 提取产品型号和名称列
        model_col = '产品型号'
        name_col = '产品名称'
        
        # 过滤掉空值
        product_data = df[[model_col, name_col]].dropna()
        logger.info(f"过滤后有 {len(product_data)} 行产品数据")
        
        # 去重，确保每个产品型号只导入一次
        unique_products = product_data.drop_duplicates(subset=[model_col])
        logger.info(f"去重后有 {len(unique_products)} 个唯一产品")
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        imported_count = 0
        for _, row in unique_products.iterrows():
            model_number = row[model_col]
            product_name = row[name_col]
            
            # 确保数据有效
            if model_number and product_name:
                # 插入产品
                cursor.execute("""
                    INSERT INTO products (model_number, name, price, is_active, created_at, updated_at)
                    VALUES (?, ?, 0.0, 1, datetime('now'), datetime('now'))
                """, (str(model_number), str(product_name)))
                imported_count += 1
                logger.debug(f"导入产品: {model_number} - {product_name}")
        
        conn.commit()
        conn.close()
        
        logger.info(f"成功导入 {imported_count} 个产品")
        return imported_count
    except Exception as e:
        logger.error(f"导入产品失败: {e}")
        return 0

def recreate_customer_products():
    """重新创建购买单位和产品的关联"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取所有活跃购买单位
        cursor.execute("SELECT id, unit_name FROM purchase_units WHERE is_active = 1")
        units = cursor.fetchall()
        logger.info(f"找到 {len(units)} 个购买单位")
        
        # 获取所有活跃产品
        cursor.execute("SELECT id, model_number, name FROM products WHERE is_active = 1")
        products = cursor.fetchall()
        logger.info(f"找到 {len(products)} 个产品")
        
        # 为每个购买单位关联所有产品
        association_count = 0
        for unit in units:
            unit_id = unit[0]
            unit_name = unit[1]
            
            for product in products:
                product_id = product[0]
                
                # 插入关联
                cursor.execute("""
                    INSERT INTO customer_products (unit_id, product_id, custom_price, is_active, created_at, updated_at)
                    VALUES (?, ?, 0.0, 1, datetime('now'), datetime('now'))
                """, (unit_id, product_id))
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
        
        # 检查产品数量
        cursor.execute("SELECT COUNT(*) FROM products WHERE is_active = 1")
        product_count = cursor.fetchone()[0]
        logger.info(f"数据库中产品数量: {product_count}")
        
        # 检查关联数量
        cursor.execute("SELECT COUNT(*) FROM customer_products WHERE is_active = 1")
        association_count = cursor.fetchone()[0]
        logger.info(f"数据库中关联数量: {association_count}")
        
        # 检查购买单位数量
        cursor.execute("SELECT COUNT(*) FROM purchase_units WHERE is_active = 1")
        unit_count = cursor.fetchone()[0]
        logger.info(f"数据库中购买单位数量: {unit_count}")
        
        conn.close()
        
        return {
            'product_count': product_count,
            'association_count': association_count,
            'unit_count': unit_count
        }
    except Exception as e:
        logger.error(f"验证导入失败: {e}")
        return None

def main():
    """主函数"""
    print("=== 清理并重新导入产品 ===")
    
    # 清理数据库
    if clean_database():
        # 导入产品
        imported_count = import_products_from_excel()
        if imported_count > 0:
            # 重新创建关联
            association_count = recreate_customer_products()
            if association_count > 0:
                # 验证导入
                result = verify_import()
                if result:
                    print(f"\n✅ 操作完成！")
                    print(f"导入产品数量: {result['product_count']}")
                    print(f"创建关联数量: {result['association_count']}")
                    print(f"购买单位数量: {result['unit_count']}")
                    return True
    
    print("\n❌ 操作失败！")
    return False

if __name__ == "__main__":
    main()
