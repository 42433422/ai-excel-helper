#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从备份恢复购买单位
"""

import sqlite3
import shutil
import datetime

def restore_purchase_units():
    """从备份恢复购买单位"""
    
    print("=== 从备份恢复购买单位 ===")
    
    # 创建当前数据库的备份
    current_backup = f'products_current_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    shutil.copy('products.db', current_backup)
    print(f'✅ 创建当前数据库备份: {current_backup}')
    
    # 连接备份数据库
    backup_conn = sqlite3.connect('products_backup.db')
    backup_cursor = backup_conn.cursor()
    
    # 连接当前数据库
    current_conn = sqlite3.connect('products.db')
    current_cursor = current_conn.cursor()
    
    try:
        # 从备份获取购买单位数据
        backup_cursor.execute('''
            SELECT unit_name, contact_person, contact_phone, address, is_active 
            FROM purchase_units
        ''')
        backup_units = backup_cursor.fetchall()
        print(f'从备份获取到 {len(backup_units)} 个购买单位')
        
        # 获取当前的所有购买单位，避免重复
        current_cursor.execute('SELECT unit_name FROM purchase_units')
        current_units = [row[0] for row in current_cursor.fetchall()]
        print(f'当前已有的购买单位数量: {len(current_units)}')
        
        # 恢复购买单位（跳过已有的单位）
        restored_count = 0
        for unit in backup_units:
            unit_name = unit[0]
            
            # 跳过已有的单位
            if unit_name in current_units:
                continue
            
            # 插入购买单位
            current_cursor.execute('''
                INSERT INTO purchase_units 
                (unit_name, contact_person, contact_phone, address, is_active)
                VALUES (?, ?, ?, ?, ?)
            ''', unit)
            restored_count += 1
        
        current_conn.commit()
        print(f'\n✅ 成功恢复 {restored_count} 个购买单位')
        
        # 验证恢复结果
        print('\n=== 验证恢复结果 ===')
        current_cursor.execute('SELECT COUNT(*) FROM purchase_units')
        total_units = current_cursor.fetchone()[0]
        print(f'恢复后总购买单位数量: {total_units}')
        
        # 检查恢复的购买单位
        current_cursor.execute('''
            SELECT id, unit_name 
            FROM purchase_units 
            ORDER BY id 
            LIMIT 10
        ''')
        restored_units = current_cursor.fetchall()
        print(f'恢复的购买单位 (前10个):')
        for unit in restored_units:
            print(f'  ID: {unit[0]}, 名称: {unit[1]}')
        
        print('\n✅ 购买单位恢复完成！前端现在应该能正常加载所有客户单位了。')
        
    except Exception as e:
        current_conn.rollback()
        print(f'❌ 恢复购买单位失败: {e}')
    finally:
        backup_conn.close()
        current_conn.close()

if __name__ == "__main__":
    restore_purchase_units()