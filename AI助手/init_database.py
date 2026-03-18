#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
创建必要的表结构
"""

import sqlite3
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def init_database(db_path='products.db'):
    """
    初始化数据库
    :param db_path: 数据库文件路径
    """
    try:
        # 检查数据库文件是否存在
        db_exists = os.path.exists(db_path)
        logger.info(f"数据库文件 {db_path} {'已存在' if db_exists else '不存在'}")
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 创建purchase_units表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS purchase_units (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit_name TEXT NOT NULL,
                contact_person TEXT,
                contact_phone TEXT,
                address TEXT,
                discount_rate REAL DEFAULT 1.0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        logger.info("创建purchase_units表成功")
        
        # 创建products表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_number TEXT,
                name TEXT NOT NULL,
                specification TEXT,
                price REAL DEFAULT 0.0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        logger.info("创建products表成功")
        
        # 创建customer_products表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customer_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit_id INTEGER,
                product_id INTEGER,
                custom_price REAL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (unit_id) REFERENCES purchase_units(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        ''')
        logger.info("创建customer_products表成功")
        
        # 创建shipment_records表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shipment_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                purchase_unit TEXT NOT NULL,
                unit_id INTEGER,
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
                FOREIGN KEY (unit_id) REFERENCES purchase_units(id)
            )
        ''')
        logger.info("创建shipment_records表成功")
        
        # 插入一些默认的购买单位
        default_units = [
            ('蕊芯', '张经理', '13800138000', '北京市朝阳区'),
            ('七彩乐园', '李经理', '13900139000', '上海市浦东新区'),
            ('金汉武', '王经理', '13700137000', '广州市天河区'),
            ('侯雪梅', '侯女士', '13600136000', '深圳市南山区'),
            ('刘英', '刘女士', '13500135000', '成都市武侯区'),
            ('国圣化工', '陈经理', '13400134000', '杭州市西湖区'),
            ('宗南', '宗先生', '13300133000', '武汉市武昌区'),
            ('宜榢', '黄经理', '13200132000', '重庆市渝中区'),
            ('小洋杨总', '杨总', '13100131000', '南京市玄武区'),
            ('尹玉华', '尹女士', '13000130000', '天津市和平区')
        ]
        
        # 检查是否已有数据
        cursor.execute('SELECT COUNT(*) FROM purchase_units')
        count = cursor.fetchone()[0]
        
        if count == 0:
            cursor.executemany('''
                INSERT INTO purchase_units (unit_name, contact_person, contact_phone, address)
                VALUES (?, ?, ?, ?)
            ''', default_units)
            logger.info(f"插入了 {len(default_units)} 个默认购买单位")
        else:
            logger.info(f"数据库中已有 {count} 个购买单位，跳过插入默认数据")
        
        # 提交更改
        conn.commit()
        logger.info("数据库初始化成功")
        
    except sqlite3.Error as e:
        logger.error(f"数据库初始化失败: {e}")
    finally:
        if conn:
            conn.close()

def check_database(db_path='products.db'):
    """
    检查数据库结构
    :param db_path: 数据库文件路径
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute('''
            SELECT name FROM sqlite_master WHERE type='table' ORDER BY name
        ''')
        tables = cursor.fetchall()
        
        logger.info("数据库中的表:")
        for table in tables:
            logger.info(f"  - {table[0]}")
        
        # 检查purchase_units表的结构
        cursor.execute('PRAGMA table_info(purchase_units)')
        columns = cursor.fetchall()
        logger.info("\npurchase_units表结构:")
        for column in columns:
            logger.info(f"  - {column[1]} ({column[2]})")
        
        # 检查数据
        cursor.execute('SELECT COUNT(*) FROM purchase_units')
        count = cursor.fetchone()[0]
        logger.info(f"\npurchase_units表中有 {count} 条记录")
        
    except sqlite3.Error as e:
        logger.error(f"检查数据库失败: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    logger.info("开始初始化数据库...")
    init_database()
    logger.info("\n检查数据库结构...")
    check_database()
    logger.info("数据库初始化完成!")
