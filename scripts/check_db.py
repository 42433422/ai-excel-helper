#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查半岛风情.db数据库结构
"""

import sqlite3
import os

db_path = r"424\半岛风情.db"

def check_database():
    """检查数据库结构和数据"""
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 获取所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"数据库中的表: {[t[0] for t in tables]}")
    
    # 检查products表
    if tables:
        table_name = tables[0][0]
        print(f"\n表名: {table_name}")
        
        # 获取表结构
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        print(f"\n表结构:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        
        # 获取数据样本
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
        rows = cursor.fetchall()
        print(f"\n数据样本 (前5条):")
        for i, row in enumerate(rows, 1):
            print(f"  记录 {i}: {row}")
        
        # 获取总记录数
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"\n总记录数: {count}")
    
    conn.close()

if __name__ == "__main__":
    check_database()

