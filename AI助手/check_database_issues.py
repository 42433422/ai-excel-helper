#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库问题
"""

import sqlite3

def check_database():
    """检查数据库问题"""
    
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()
    
    print("=== 检查数据库表 ===")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    for table in tables:
        print(f"表: {table[0]}")
    
    print("\n=== 检查purchase_units表 ===")
    try:
        cursor.execute("SELECT COUNT(*) FROM purchase_units")
        count = cursor.fetchone()[0]
        print(f"purchase_units表存在，有{count}条记录")
        
        # 显示前几条记录
        cursor.execute("SELECT * FROM purchase_units LIMIT 5")
        records = cursor.fetchall()
        for record in records:
            print(f"  记录: {record}")
            
    except Exception as e:
        print(f"❌ purchase_units表不存在或查询失败: {e}")
    
    print("\n=== 检查products表 ===")
    try:
        cursor.execute("PRAGMA table_info(products)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"字段: {col[1]} ({col[2]})")
    except Exception as e:
        print(f"❌ products表检查失败: {e}")
    
    conn.close()

if __name__ == "__main__":
    check_database()