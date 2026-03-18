#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完全清理数据库，准备重新导入
"""

import sqlite3
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

db_path = "products.db"

def clean_database():
    """完全清理数据库"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 删除所有表的数据
        cursor.execute("DELETE FROM customer_products")
        logger.info("清理了customer_products表")
        
        cursor.execute("DELETE FROM products")
        logger.info("清理了products表")
        
        cursor.execute("DELETE FROM purchase_units")
        logger.info("清理了purchase_units表")
        
        # 重置自增计数器
        cursor.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name = 'customer_products'")
        cursor.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name = 'products'")
        cursor.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name = 'purchase_units'")
        logger.info("重置了自增计数器")
        
        conn.commit()
        conn.close()
        
        logger.info("数据库清理完成")
        return True
    except Exception as e:
        logger.error(f"清理数据库失败: {e}")
        return False

def verify_clean():
    """验证数据库已清理"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查各表的数据量
        tables = ['purchase_units', 'products', 'customer_products']
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            logger.info(f"{table}表: {count} 条记录")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"验证清理失败: {e}")
        return False

def main():
    """主函数"""
    print("=== 完全清理数据库 ===")
    
    if clean_database():
        verify_clean()
        print("\n✅ 数据库清理完成！")
        print("可以重新导入新的文件了。")
        return True
    else:
        print("\n❌ 数据库清理失败！")
        return False

if __name__ == "__main__":
    main()
