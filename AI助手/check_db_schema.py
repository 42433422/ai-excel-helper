#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库表结构
"""

import sqlite3

def check_db_schema():
    """检查数据库表结构"""
    
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()
    
    print("=== 检查数据库表结构 ===")
    
    try:
        # 检查表结构
        tables = ['purchase_units', 'products']
        for table in tables:
            print(f"\n📄 表: {table}")
            
            # 检查表结构
            cursor.execute(f'PRAGMA table_info({table})')
            columns = cursor.fetchall()
            
            for col in columns:
                print(f"  {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULL'}")
        
        # 检查现有购买单位
        print("\n=== 检查现有购买单位 ===")
        cursor.execute('SELECT id, unit_name FROM purchase_units LIMIT 10')
        units = cursor.fetchall()
        
        print(f"找到 {len(units)} 个购买单位:")
        for unit in units:
            print(f"  ID: {unit[0]}, 名称: {unit[1]}")
        
    except Exception as e:
        print(f"❌ 检查数据库失败: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_db_schema()