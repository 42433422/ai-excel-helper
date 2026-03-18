#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建订单相关数据表
"""

import sqlite3
import logging

logger = logging.getLogger(__name__)

def create_order_tables():
    """创建订单相关数据表"""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        print("开始创建订单相关数据表...")
        
        # 创建订单主表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT UNIQUE NOT NULL,
                purchase_unit TEXT NOT NULL,
                unit_id INTEGER,
                total_amount REAL DEFAULT 0,
                total_quantity_kg REAL DEFAULT 0,
                total_quantity_tins INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                raw_text TEXT,
                parsed_data TEXT,
                FOREIGN KEY (unit_id) REFERENCES purchase_units(id)
            )
        ''')
        print("✅ 创建orders表成功")
        
        # 为order_number添加索引，提高搜索性能
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_order_number ON orders(order_number)')
        print("✅ 创建订单编号索引成功")
        
        # 修改shipment_records表，添加order_id字段
        try:
            # 检查order_id字段是否存在
            cursor.execute('PRAGMA table_info(shipment_records);')
            columns = cursor.fetchall()
            has_order_id = any('order_id' in column[1] for column in columns)
            
            if not has_order_id:
                cursor.execute('ALTER TABLE shipment_records ADD COLUMN order_id INTEGER')
                print("✅ 为shipment_records表添加order_id字段成功")
                
                # 添加外键约束
                # SQLite不支持直接修改表添加外键，所以我们创建新表并迁移数据
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS shipment_records_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        purchase_unit TEXT NOT NULL,
                        unit_id INTEGER,
                        order_id INTEGER,
                        product_name TEXT NOT NULL,
                        model_number TEXT,
                        quantity_kg REAL NOT NULL,
                        quantity_tins INTEGER NOT NULL,
                        tin_spec REAL,
                        unit_price REAL DEFAULT 0,
                        amount REAL DEFAULT 0,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        raw_text TEXT,
                        parsed_data TEXT,
                        FOREIGN KEY (order_id) REFERENCES orders(id)
                    )
                ''')
                
                # 迁移数据
                cursor.execute('''
                    INSERT INTO shipment_records_new (
                        id, purchase_unit, unit_id, product_name, model_number,
                        quantity_kg, quantity_tins, tin_spec, unit_price, amount,
                        status, created_at, updated_at, raw_text, parsed_data
                    ) SELECT 
                        id, purchase_unit, unit_id, product_name, model_number,
                        quantity_kg, quantity_tins, tin_spec, unit_price, amount,
                        status, created_at, updated_at, raw_text, parsed_data
                    FROM shipment_records
                ''')
                
                # 删除旧表
                cursor.execute('DROP TABLE shipment_records')
                
                # 重命名新表
                cursor.execute('ALTER TABLE shipment_records_new RENAME TO shipment_records')
                print("✅ 迁移shipment_records表数据成功")
            else:
                print("⚠️ shipment_records表已包含order_id字段")
                
        except Exception as e:
            print(f"⚠️ 修改shipment_records表时出错: {e}")
            print("⚠️ 继续执行其他操作")
        
        conn.commit()
        conn.close()
        
        print("\n✅ 所有订单相关数据表创建完成！")
        
    except Exception as e:
        print(f"❌ 创建订单数据表失败: {e}")
        raise

def check_order_tables():
    """检查订单表结构"""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        print("\n检查订单表结构:")
        
        # 检查orders表
        cursor.execute('PRAGMA table_info(orders);')
        columns = cursor.fetchall()
        print('orders表结构:')
        for column in columns:
            print(f"  - {column[1]} ({column[2]}) {'PRIMARY KEY' if column[5] else ''}")
        
        # 检查shipment_records表
        cursor.execute('PRAGMA table_info(shipment_records);')
        columns = cursor.fetchall()
        print('\nshipment_records表结构:')
        for column in columns:
            print(f"  - {column[1]} ({column[2]}) {'PRIMARY KEY' if column[5] else ''}")
        
        conn.close()
        
    except Exception as e:
        print(f"检查订单表结构失败: {e}")

if __name__ == '__main__':
    create_order_tables()
    check_order_tables()
