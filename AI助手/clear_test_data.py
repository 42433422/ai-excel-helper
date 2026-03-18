#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清空数据库中的测试数据
"""

import sqlite3

def clear_test_data():
    """清空测试数据"""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # 清空orders表
        cursor.execute('DELETE FROM orders')
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        print(f"✅ 成功清空 {deleted_count} 条测试订单")
        return True
        
    except Exception as e:
        print(f"❌ 清空测试数据失败: {e}")
        return False

if __name__ == '__main__':
    clear_test_data()
