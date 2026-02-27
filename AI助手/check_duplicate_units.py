#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查重复的购买单位
"""

import sqlite3

def check_duplicate_units():
    """检查数据库中是否有重复的购买单位"""
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()
    
    try:
        # 查询重复的购买单位
        cursor.execute('''
        SELECT unit_name, COUNT(*) as count 
        FROM purchase_units 
        GROUP BY unit_name 
        HAVING count > 1
        ''')
        
        duplicates = cursor.fetchall()
        
        print("=== 检查重复购买单位 ===")
        if duplicates:
            print("发现重复的购买单位:")
            for unit_name, count in duplicates:
                print(f"  {unit_name}: {count}个重复")
        else:
            print("✅ 无重复的购买单位")
        
        # 显示所有购买单位
        cursor.execute('SELECT id, unit_name FROM purchase_units ORDER BY unit_name')
        all_units = cursor.fetchall()
        
        print(f"\n=== 所有购买单位 ({len(all_units)}个) ===")
        for unit_id, unit_name in all_units:
            print(f"  ID: {unit_id}, 名称: {unit_name}")
            
    except Exception as e:
        print(f"❌ 检查失败: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_duplicate_units()
