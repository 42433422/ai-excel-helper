#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
添加测试订单数据来演示购买单位筛选功能
"""

import sqlite3
from datetime import datetime, timedelta

def add_test_orders():
    """添加测试订单数据"""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # 测试订单数据
        test_orders = [
            {
                'order_number': 'ORD-2026-001',
                'purchase_unit': '七彩乐园',
                'total_amount': 12500.50,
                'status': 'completed',
                'created_at': datetime.now() - timedelta(days=5),
                'updated_at': datetime.now() - timedelta(days=3)
            },
            {
                'order_number': 'ORD-2026-002',
                'purchase_unit': '迎扬电视墙',
                'total_amount': 8900.00,
                'status': 'processing',
                'created_at': datetime.now() - timedelta(days=4),
                'updated_at': datetime.now() - timedelta(days=2)
            },
            {
                'order_number': 'ORD-2026-003',
                'purchase_unit': '侯雪梅',
                'total_amount': 15600.75,
                'status': 'completed',
                'created_at': datetime.now() - timedelta(days=3),
                'updated_at': datetime.now() - timedelta(days=1)
            },
            {
                'order_number': 'ORD-2026-004',
                'purchase_unit': '博旺家私',
                'total_amount': 22300.00,
                'status': 'pending',
                'created_at': datetime.now() - timedelta(days=2),
                'updated_at': datetime.now() - timedelta(days=2)
            },
            {
                'order_number': 'ORD-2026-005',
                'purchase_unit': '金汉武',
                'total_amount': 9800.25,
                'status': 'completed',
                'created_at': datetime.now() - timedelta(days=1),
                'updated_at': datetime.now() - timedelta(hours=12)
            },
            {
                'order_number': 'ORD-2026-006',
                'purchase_unit': '中江博郡家私',
                'total_amount': 18750.50,
                'status': 'processing',
                'created_at': datetime.now() - timedelta(hours=6),
                'updated_at': datetime.now() - timedelta(hours=2)
            }
        ]

        # 插入测试订单
        for order in test_orders:
            cursor.execute('''
                INSERT INTO orders (order_number, purchase_unit, total_amount, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                order['order_number'],
                order['purchase_unit'],
                order['total_amount'],
                order['status'],
                order['created_at'].isoformat(),
                order['updated_at'].isoformat()
            ))

        conn.commit()
        
        # 验证插入结果
        cursor.execute('SELECT COUNT(*) FROM orders')
        count = cursor.fetchone()[0]
        print(f'✅ 成功添加 {len(test_orders)} 条测试订单')
        print(f'📊 数据库中现在共有 {count} 条订单')
        
        # 显示购买单位统计
        cursor.execute('SELECT purchase_unit, COUNT(*) FROM orders GROUP BY purchase_unit ORDER BY purchase_unit')
        units = cursor.fetchall()
        print('\n📋 购买单位统计:')
        for unit, cnt in units:
            print(f'   - {unit}: {cnt} 个订单')

        conn.close()
        return True
        
    except Exception as e:
        print(f'❌ 添加测试数据失败: {e}')
        return False

if __name__ == '__main__':
    success = add_test_orders()
    if success:
        print('\n🎉 测试数据添加完成！现在可以测试购买单位筛选功能了。')
    else:
        print('\n❌ 测试数据添加失败！')
