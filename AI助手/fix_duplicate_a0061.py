#!/usr/bin/env python3
# 修复A0061的重复记录

import sqlite3
import os

def fix_duplicate_a0061():
    """修复A0061的重复记录"""
    print("=== 修复A0061的重复记录 ===")
    
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, 'products.db')
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取蕊芯家私1的购买单位ID
        cursor.execute("SELECT id FROM purchase_units WHERE unit_name = ?", ("蕊芯家私1",))
        result = cursor.fetchone()
        
        if not result:
            print("❌ 未找到蕊芯家私1的购买单位")
            conn.close()
            return False
        
        unit_id = result[0]
        
        # 查找A0061的重复记录
        cursor.execute("""
            SELECT cp.id, cp.custom_price, p.name, p.model_number
            FROM customer_products cp
            JOIN products p ON cp.product_id = p.id
            WHERE cp.unit_id = ? AND p.model_number = 'A0061' AND cp.is_active = 1
            ORDER BY cp.created_at
        """, (unit_id,))
        
        duplicates = cursor.fetchall()
        
        if len(duplicates) > 1:
            print(f"发现 {len(duplicates)} 个A0061记录:")
            for record_id, price, name, model in duplicates:
                print(f"  ID: {record_id}, 价格: {price}元, 产品: {name}")
            
            # 保留最新的记录，删除其他记录
            keep_record = duplicates[-1]  # 保留最新的
            delete_records = duplicates[:-1]  # 删除其他的
            
            print(f"\n保留记录: ID {keep_record[0]}, 价格 {keep_record[1]}元")
            
            for record_id, price, name, model in delete_records:
                cursor.execute("""
                    UPDATE customer_products 
                    SET is_active = 0, updated_at = datetime('now')
                    WHERE id = ?
                """, (record_id,))
                print(f"删除重复记录: ID {record_id}, 价格 {price}元")
            
            conn.commit()
            print("✅ A0061重复记录已修复")
            
        else:
            print("✅ 没有发现A0061重复记录")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        return False

if __name__ == "__main__":
    fix_duplicate_a0061()