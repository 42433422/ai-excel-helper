#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查产品文件夹中的数据库结构
"""

import sqlite3
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_database_structure(db_path):
    """
    检查数据库结构
    :param db_path: 数据库文件路径
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(db_path):
            logger.error(f"数据库文件不存在: {db_path}")
            return False
        
        logger.info(f"检查数据库文件: {db_path}")
        
        # 连接数据库
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
        
        # 检查每个表的结构
        for table in tables:
            table_name = table[0]
            logger.info(f"\n{table_name}表结构:")
            cursor.execute(f'PRAGMA table_info({table_name})')
            columns = cursor.fetchall()
            for column in columns:
                logger.info(f"  - {column[1]} ({column[2]})")
        
        # 检查数据
        for table in tables:
            table_name = table[0]
            try:
                cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
                count = cursor.fetchone()[0]
                logger.info(f"{table_name}表中有 {count} 条记录")
            except sqlite3.Error as e:
                logger.warning(f"无法查询{table_name}表数据: {e}")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        logger.error(f"数据库错误: {e}")
        return False

def main():
    """
    主函数
    """
    # 检查产品文件夹中的数据库
    db_path = '产品文件夹/customer_products_final_corrected.db'
    logger.info("=== 检查产品文件夹中的数据库 ===")
    check_database_structure(db_path)
    
    # 检查当前目录中的数据库
    db_path = 'products.db'
    logger.info("\n=== 检查当前目录中的数据库 ===")
    check_database_structure(db_path)

if __name__ == '__main__':
    main()
