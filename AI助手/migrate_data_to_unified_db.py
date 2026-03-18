#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将独立单位数据库的数据迁移到统一数据库
"""

import os
import sqlite3
import glob
from datetime import datetime

def migrate_unit_databases_to_unified():
    """将单位独立数据库迁移到统一数据库"""
    
    print("=== 开始数据迁移 ===")
    
    # 连接统一数据库
    unified_db = 'products.db'
    conn = sqlite3.connect(unified_db)
    cursor = conn.cursor()
    
    # 检查表结构
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customer_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unit_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            custom_price REAL,
            is_active BOOLEAN DEFAULT 1,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (unit_id) REFERENCES purchase_units(id),
            FOREIGN KEY (product_id) REFERENCES products(id),
            UNIQUE(unit_id, product_id)
        )
    """)
    
    # 获取所有单位数据库
    units_dir = 'unit_databases'
    unit_dbs = glob.glob(os.path.join(units_dir, '*.db'))
    
    print(f"找到 {len(unit_dbs)} 个单位数据库")
    
    # 统计信息
    migrated_products = 0
    migrated_associations = 0
    
    # 获取客户ID映射（unit_name -> id）
    cursor.execute("SELECT id, unit_name FROM purchase_units WHERE is_active = 1")
    unit_name_to_id = {name: id for id, name in cursor.fetchall()}
    
    print(f"统一数据库中有 {len(unit_name_to_id)} 个客户")
    
    for unit_db_path in unit_dbs:
        unit_name = os.path.basename(unit_db_path)[:-3]  # 移除 .db 后缀
        
        if unit_name not in unit_name_to_id:
            print(f"跳过未找到的客户: {unit_name}")
            continue
            
        unit_id = unit_name_to_id[unit_name]
        print(f"处理客户: {unit_name} (ID: {unit_id})")
        
        try:
            # 连接单位数据库
            unit_conn = sqlite3.connect(unit_db_path)
            unit_cursor = unit_conn.cursor()
            
            # 获取产品
            unit_cursor.execute("SELECT * FROM products")
            unit_products = unit_cursor.fetchall()
            
            print(f"  - 找到 {len(unit_products)} 个产品")
            
            # 迁移每个产品
            for unit_product in unit_products:
                # 检查产品是否已存在
                model_number = unit_product[1] if len(unit_product) > 1 else ''
                name = unit_product[2] if len(unit_product) > 2 else ''
                
                cursor.execute(
                    "SELECT id FROM products WHERE model_number = ? AND name = ?",
                    (model_number, name)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # 产品已存在，使用现有ID
                    product_id = existing[0]
                else:
                    # 插入新产品
                    cursor.execute("""
                        INSERT INTO products (model_number, name, specification, price, quantity, 
                                          description, category, brand, unit, is_active, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                    """, (
                        model_number, name,
                        unit_product[3] if len(unit_product) > 3 else '',
                        unit_product[4] if len(unit_product) > 4 else 0,
                        unit_product[5] if len(unit_product) > 5 else 1,
                        unit_product[6] if len(unit_product) > 6 else '',
                        unit_product[7] if len(unit_product) > 7 else '',
                        unit_product[8] if len(unit_product) > 8 else '',
                        unit_product[9] if len(unit_product) > 9 else '',
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))
                    product_id = cursor.lastrowid
                    migrated_products += 1
                
                # 创建关联关系
                cursor.execute(
                    "SELECT id FROM customer_products WHERE unit_id = ? AND product_id = ?",
                    (unit_id, product_id)
                )
                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO customer_products (unit_id, product_id, is_active, created_at, updated_at)
                        VALUES (?, ?, 1, ?, ?)
                    """, (unit_id, product_id, datetime.now().isoformat(), datetime.now().isoformat()))
                    migrated_associations += 1
            
            unit_conn.close()
            
        except Exception as e:
            print(f"  - 处理客户 {unit_name} 时出错: {e}")
    
    # 提交更改
    conn.commit()
    
    print(f"\n=== 迁移完成 ===")
    print(f"迁移产品数: {migrated_products}")
    print(f"迁移关联数: {migrated_associations}")
    
    # 显示最终统计
    cursor.execute("SELECT COUNT(*) FROM products")
    total_products = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM customer_products")
    total_associations = cursor.fetchone()[0]
    
    print(f"统一数据库现有产品: {total_products}")
    print(f"统一数据库现有关联: {total_associations}")
    
    conn.close()
    
    return migrated_products, migrated_associations

if __name__ == "__main__":
    migrate_unit_databases_to_unified()
