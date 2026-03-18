#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合并金汉武相关的购买单位
"""

import sqlite3
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

db_path = "products.db"

def merge_jinhanwu_units():
    """合并金汉武相关的购买单位"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 找到金汉武相关的购买单位
        cursor.execute("""
            SELECT id, unit_name 
            FROM purchase_units 
            WHERE unit_name LIKE '%金汉武%' 
            ORDER BY unit_name
        """)
        
        jinhanwu_units = cursor.fetchall()
        logger.info(f"找到金汉武相关单位: {[unit[1] for unit in jinhanwu_units]}")
        
        if len(jinhanwu_units) <= 1:
            logger.info("只有1个或没有金汉武单位，无需合并")
            return True
        
        # 选择主要单位（金汉武）
        main_unit = None
        for unit_id, unit_name in jinhanwu_units:
            if unit_name == '金汉武':
                main_unit = (unit_id, unit_name)
                break
        
        if not main_unit:
            # 如果没有"金汉武"，选择第一个作为主单位
            main_unit = jinhanwu_units[0]
            logger.info(f"选择主单位: {main_unit[1]}")
        
        # 获取主单位的产品关联
        cursor.execute("""
            SELECT product_id, custom_price 
            FROM customer_products 
            WHERE unit_id = ? AND is_active = 1
        """, (main_unit[0],))
        
        main_products = {row[0]: row[1] for row in cursor.fetchall()}
        logger.info(f"主单位 {main_unit[1]} 现有产品: {len(main_products)} 个")
        
        # 合并其他单位
        merged_count = 0
        for unit_id, unit_name in jinhanwu_units:
            if unit_id == main_unit[0]:  # 跳过主单位
                continue
            
            logger.info(f"合并单位: {unit_name} (ID: {unit_id})")
            
            # 获取该单位的产品关联
            cursor.execute("""
                SELECT product_id, custom_price 
                FROM customer_products 
                WHERE unit_id = ? AND is_active = 1
            """, (unit_id,))
            
            unit_products = {row[0]: row[1] for row in cursor.fetchall()}
            logger.info(f"  - {unit_name} 有 {len(unit_products)} 个产品")
            
            # 合并产品关联（避免重复）
            for product_id, custom_price in unit_products.items():
                if product_id in main_products:
                    # 如果已存在，保持原价格或选择较高的价格
                    if custom_price > main_products[product_id]:
                        cursor.execute("""
                            UPDATE customer_products 
                            SET custom_price = ?, updated_at = datetime('now')
                            WHERE unit_id = ? AND product_id = ?
                        """, (custom_price, main_unit[0], product_id))
                        main_products[product_id] = custom_price
                else:
                    # 如果不存在，添加到主单位
                    cursor.execute("""
                        INSERT INTO customer_products (unit_id, product_id, custom_price, is_active, created_at, updated_at)
                        VALUES (?, ?, ?, 1, datetime('now'), datetime('now'))
                    """, (main_unit[0], product_id, custom_price))
                    main_products[product_id] = custom_price
                    merged_count += 1
            
            # 禁用该单位
            cursor.execute("""
                UPDATE purchase_units 
                SET is_active = 0, updated_at = datetime('now')
                WHERE id = ?
            """, (unit_id,))
            
            # 删除该单位的所有关联（因为已经转移到主单位）
            cursor.execute("""
                DELETE FROM customer_products 
                WHERE unit_id = ?
            """, (unit_id,))
        
        conn.commit()
        
        # 验证合并结果
        cursor.execute("""
            SELECT COUNT(*) 
            FROM customer_products 
            WHERE unit_id = ? AND is_active = 1
        """, (main_unit[0],))
        
        final_count = cursor.fetchone()[0]
        
        logger.info(f"合并完成:")
        logger.info(f"  - 主单位: {main_unit[1]} (ID: {main_unit[0]})")
        logger.info(f"  - 合并了 {len(jinhanwu_units)-1} 个单位")
        logger.info(f"  - 新增了 {merged_count} 个产品关联")
        logger.info(f"  - 最终产品数量: {final_count} 个")
        
        # 列出所有相关的购买单位状态
        cursor.execute("""
            SELECT unit_name, is_active, (SELECT COUNT(*) FROM customer_products WHERE unit_id = purchase_units.id AND is_active = 1) as product_count
            FROM purchase_units 
            WHERE unit_name LIKE '%金汉武%'
            ORDER BY is_active DESC, product_count DESC
        """)
        
        results = cursor.fetchall()
        logger.info("金汉武相关单位状态:")
        for unit_name, is_active, product_count in results:
            status = "启用" if is_active else "禁用"
            logger.info(f"  - {unit_name}: {status}, {product_count} 个产品")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"合并金汉武单位失败: {e}")
        return False

def verify_merge():
    """验证合并结果"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查总购买单位数量
        cursor.execute("SELECT COUNT(*) FROM purchase_units WHERE is_active = 1")
        total_units = cursor.fetchone()[0]
        
        # 检查金汉武相关单位
        cursor.execute("SELECT COUNT(*) FROM purchase_units WHERE unit_name LIKE '%金汉武%' AND is_active = 1")
        active_jinhanwu = cursor.fetchone()[0]
        
        # 检查产品关联
        cursor.execute("SELECT COUNT(*) FROM customer_products WHERE is_active = 1")
        total_associations = cursor.fetchone()[0]
        
        logger.info(f"合并验证:")
        logger.info(f"  - 总购买单位: {total_units} 个")
        logger.info(f"  - 金汉武相关单位: {active_jinhanwu} 个")
        logger.info(f"  - 总产品关联: {total_associations} 个")
        
        # 检查主要金汉武单位的产品数量
        cursor.execute("""
            SELECT pu.unit_name, COUNT(cp.id) as product_count
            FROM purchase_units pu
            JOIN customer_products cp ON pu.id = cp.unit_id AND cp.is_active = 1
            WHERE pu.unit_name LIKE '%金汉武%'
            GROUP BY pu.id, pu.unit_name
            ORDER BY product_count DESC
        """)
        
        results = cursor.fetchall()
        logger.info("金汉武相关单位产品统计:")
        for unit_name, product_count in results:
            logger.info(f"  - {unit_name}: {product_count} 个产品")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"验证合并失败: {e}")
        return False

def main():
    """主函数"""
    print("=== 合并金汉武相关购买单位 ===")
    
    if merge_jinhanwu_units():
        if verify_merge():
            print("\n✅ 金汉武单位合并成功！")
            print("所有金汉武相关的购买单位已合并为'金汉武'")
            return True
        else:
            print("\n❌ 验证失败！")
    else:
        print("\n❌ 合并失败！")
    
    return False

if __name__ == "__main__":
    main()
