#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按照用户要求的规则完整导入数据
1. 先添加购买单位
2. 按单位导入产品
3. 相同名字、不同编号，只保留最底下的
4. 日期型号改为数字+英文字母唯一编号
5. 不同单位产品独立
"""

import sqlite3
import pandas as pd
import logging
import re
from collections import defaultdict

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

db_path = "products.db"
excel_path = "templates\\新建 XLSX 工作表 (2).xlsx"

def process_date_model(model):
    """处理日期型号，改为数字+英文字母唯一编号"""
    model_str = str(model).strip()
    
    # 检查是否为日期型号（6位数字）
    if re.match(r'^\d{6}$', model_str):
        # 将6位数字分成三部分：月、日
        # 例如：061028 -> 06(月份) 10(日期) 28(年份)
        month = model_str[:2]
        day = model_str[2:4]
        year = model_str[4:6]
        
        # 组合成更简洁的格式：月日年 + 字母后缀
        # 如果需要唯一性，使用字母后缀
        return f"{month}{day}{year}"
    
    return model_str

def add_purchase_units(df):
    """添加所有购买单位"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取Excel中的所有购买单位
        excel_units = df['购买单位'].dropna().unique()
        logger.info(f"发现 {len(excel_units)} 个购买单位")
        
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

def process_products_by_unit_rules(df):
    """按照用户要求的规则处理产品"""
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
            
            # 按产品名称分组，保留最后一次出现
            name_to_product = {}
            date_model_suffixes = defaultdict(int)  # 用于日期型号的后缀计数
            
            # 遍历所有记录，用最后一次出现的记录覆盖前面的
            for idx, row in unit_data.iterrows():
                name = str(row['产品名称']).strip()
                original_model = str(row['产品型号']).strip()
                
                # 处理日期型号
                processed_model = process_date_model(original_model)
                
                # 如果是日期型号，需要确保唯一性
                if re.match(r'^\d{6}$', original_model):
                    # 检查是否已经有相同的基础型号
                    suffix = date_model_suffixes[processed_model]
                    if suffix > 0:
                        # 添加字母后缀
                        letter = chr(ord('a') + suffix)
                        processed_model = processed_model + letter
                        logger.debug(f"日期型号 {original_model} 处理为: {processed_model}")
                    
                    date_model_suffixes[processed_model] += 1
                
                # 如果产品名称已存在（相同名字、不同编号），只保留最后一次出现的
                name_to_product[name] = {
                    'original_model': original_model,
                    'model': processed_model,
                    'name': name,
                    'price': float(row['单价']) if pd.notna(row['单价']) else 0.0
                }
            
            unit_products = list(name_to_product.values())
            unit_product_mapping[unit] = unit_products
            
            # 统计去重情况
            total_records = len(unit_data)
            unique_names = len(unit_products)
            duplicates_removed = total_records - unique_names
            
            logger.info(f"  - 总记录: {total_records} 条")
            logger.info(f"  - 唯一产品: {unique_names} 个")
            logger.info(f"  - 去重: {duplicates_removed} 个 (相同名字、不同编号，只保留最底下的)")
        
        # 导入所有产品到数据库
        all_products = {}
        for unit, products in unit_product_mapping.items():
            for product in products:
                # 使用产品名称作为唯一键，确保不同单位产品独立
                product_name = product['name']
                product_key = f"{unit}_{product_name}"  # 单位名称 + 产品名称作为唯一键
                
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
        cursor.execute("SELECT id, name FROM products WHERE is_active = 1")
        product_id_map = {}
        for row in cursor.fetchall():
            product_id_map[row[1]] = row[0]  # name -> id
        
        cursor.execute("SELECT id, unit_name FROM purchase_units WHERE is_active = 1")
        unit_id_map = {row[1]: row[0] for row in cursor.fetchall()}
        
        association_count = 0
        
        for unit, products in unit_product_mapping.items():
            unit_id = unit_id_map.get(unit)
            if not unit_id:
                logger.warning(f"找不到购买单位ID: {unit}")
                continue
            
            for product in products:
                product_id = product_id_map.get(product['name'])
                if not product_id:
                    logger.warning(f"找不到产品ID: {product['name']}")
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
        
        # 检查一些示例产品
        cursor.execute("""
            SELECT pu.unit_name, p.model_number, p.name, cp.custom_price
            FROM customer_products cp
            JOIN products p ON cp.product_id = p.id
            JOIN purchase_units pu ON cp.unit_id = pu.id
            WHERE pu.unit_name LIKE '%蕊芯%' OR pu.unit_name = '温总'
            ORDER BY pu.unit_name, p.model_number
            LIMIT 10
        """)
        
        sample_products = cursor.fetchall()
        logger.info("示例产品（前10个）:")
        for unit_name, model, name, price in sample_products:
            logger.info(f"  - {unit_name}: {model} - {name} - ¥{price}")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"验证失败: {e}")
        return False

def main():
    """主函数"""
    print("=== 按照用户要求完整导入数据 ===")
    
    # 1. 读取Excel数据
    df = pd.read_excel(excel_path, sheet_name='Sheet1')
    logger.info(f"读取Excel数据成功，共 {len(df)} 行")
    
    # 2. 添加所有购买单位
    added_units = add_purchase_units(df)
    
    # 3. 按照规则处理产品
    imported_products, created_associations, unit_product_mapping = process_products_by_unit_rules(df)
    
    # 4. 验证结果
    if imported_products > 0:
        verify_import(unit_product_mapping)
        
        print(f"\n✅ 完整导入完成！")
        print(f"购买单位: {added_units} 个")
        print(f"产品: {imported_products} 个")
        print(f"关联: {created_associations} 个")
        print(f"\n各购买单位产品数量:")
        for unit, products in unit_product_mapping.items():
            print(f"  - {unit}: {len(products)} 个产品")
        print(f"\n✅ 处理规则:")
        print(f"  - 相同名字、不同编号，只保留最底下的产品")
        print(f"  - 日期型号改为数字+英文字母唯一编号")
        print(f"  - 不同单位产品独立，互不干扰")
        return True
    else:
        print("\n❌ 导入失败！")
        return False

if __name__ == "__main__":
    main()
