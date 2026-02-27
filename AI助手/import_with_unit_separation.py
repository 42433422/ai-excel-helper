#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按购买单位分类导入，处理重复产品，日期型号加字母后缀
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

def add_all_purchase_units(df):
    """添加所有购买单位"""
    try:
        # 连接数据库
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

def process_products_by_unit(df):
    """按购买单位处理产品，去重并处理日期型号"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 清理现有产品数据
        cursor.execute("DELETE FROM products")
        cursor.execute("DELETE FROM customer_products")
        cursor.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name = 'products'")
        cursor.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name = 'customer_products'")
        logger.info("清理了现有产品和关联数据")
        
        # 清理数据
        df_clean = df.dropna(subset=['购买单位', '产品型号', '产品名称', '单价']).copy()
        df_clean = df_clean[df_clean['产品型号'] != '']
        df_clean = df_clean[df_clean['产品名称'] != '']
        logger.info(f"清理后数据: {len(df_clean)} 行")
        
        # 按购买单位分组处理
        unit_product_mapping = {}
        imported_products = {}
        
        for unit in df_clean['购买单位'].unique():
            unit_data = df_clean[df_clean['购买单位'] == unit]
            logger.info(f"处理购买单位 '{unit}' 的 {len(unit_data)} 条产品记录")
            
            # 按产品型号分组
            model_groups = unit_data.groupby('产品型号')
            unit_products = []
            
            for model, group in model_groups:
                # 保留最后一次出现的记录（按索引顺序）
                latest_record = group.iloc[-1]
                
                # 处理日期型号
                processed_model = process_date_model(model, group, unit)
                
                # 检查名称是否重复（相同型号不同名称）
                if len(group['产品名称'].unique()) > 1:
                    # 保留最后一次出现的名称
                    latest_name = latest_record['产品名称']
                    logger.debug(f"型号 '{model}' 在单位 '{unit}' 中有多个名称，保留: {latest_name}")
                
                unit_products.append({
                    'original_model': model,
                    'model': processed_model,
                    'name': latest_record['产品名称'],
                    'price': float(latest_record['单价']) if pd.notna(latest_record['单价']) else 0.0
                })
            
            unit_product_mapping[unit] = unit_products
        
        # 导入所有产品到数据库
        all_products = []
        for unit, products in unit_product_mapping.items():
            for product in products:
                # 检查是否已存在（避免重复导入）
                exists = False
                for existing in all_products:
                    if existing['model'] == product['model']:
                        exists = True
                        break
                
                if not exists:
                    all_products.append(product)
        
        logger.info(f"导入 {len(all_products)} 个唯一产品")
        
        # 插入产品到数据库
        for product in all_products:
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

def process_date_model(model, group, unit):
    """处理日期型号，添加英文字母后缀"""
    import re
    
    model_str = str(model).strip()
    
    # 检查是否为日期型号（6位数字）
    if re.match(r'^\d{6}$', model_str):
        # 统计该型号在当前单位中的出现次数
        count = len(group)
        
        if count == 1:
            # 只出现一次，直接返回
            return model_str
        else:
            # 出现多次，添加英文字母后缀
            # 从 'a' 开始，'a', 'b', 'c' ...
            suffix = chr(ord('a') + (count - 1))
            new_model = model_str + suffix
            
            logger.debug(f"日期型号 '{model_str}' 在单位 '{unit}' 中出现{count}次，处理为: {new_model}")
            return new_model
    
    return model_str

def create_unit_associations(conn, unit_product_mapping):
    """为每个单位创建产品关联"""
    try:
        cursor = conn.cursor()
        
        # 获取所有产品和购买单位的ID映射
        cursor.execute("SELECT id, model_number FROM products WHERE is_active = 1")
        product_id_map = {row[1]: row[0] for row in cursor.fetchall()}
        
        cursor.execute("SELECT id, unit_name FROM purchase_units WHERE is_active = 1")
        unit_id_map = {row[1]: row[0] for row in cursor.fetchall()}
        
        association_count = 0
        
        for unit, products in unit_product_mapping.items():
            unit_id = unit_id_map.get(unit)
            if not unit_id:
                logger.warning(f"找不到购买单位ID: {unit}")
                continue
            
            for product in products:
                product_id = product_id_map.get(product['model'])
                if not product_id:
                    logger.warning(f"找不到产品ID: {product['model']}")
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
    print("=== 按购买单位分类导入产品 ===")
    
    # 1. 读取Excel数据
    df = pd.read_excel(excel_path, sheet_name='Sheet1')
    logger.info(f"读取Excel数据成功，共 {len(df)} 行")
    
    # 2. 添加所有购买单位
    added_units = add_all_purchase_units(df)
    
    # 3. 按单位处理产品
    imported_products, created_associations, unit_product_mapping = process_products_by_unit(df)
    
    # 4. 验证结果
    if imported_products > 0:
        verify_import(unit_product_mapping)
        
        print(f"\n✅ 导入完成！")
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

if __name__ == "__main__":
    main()
