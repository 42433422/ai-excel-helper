#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建customer_products表并为购买单位关联产品
"""

import sqlite3
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

db_path = "products.db"

def create_customer_products_table():
    """创建customer_products表"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 创建customer_products表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customer_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                custom_price REAL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (unit_id) REFERENCES purchase_units(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_customer_products_unit_id ON customer_products(unit_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_customer_products_product_id ON customer_products(product_id)")
        
        conn.commit()
        conn.close()
        
        logger.info("成功创建customer_products表")
        return True
    except Exception as e:
        logger.error(f"创建customer_products表失败: {e}")
        return False

def associate_products_with_units():
    """为购买单位关联产品"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取所有活跃产品
        cursor.execute("SELECT id, model_number, name, price FROM products WHERE is_active = 1")
        products = cursor.fetchall()
        
        # 获取所有活跃购买单位
        cursor.execute("SELECT id, unit_name FROM purchase_units WHERE is_active = 1")
        units = cursor.fetchall()
        
        logger.info(f"找到 {len(products)} 个产品，{len(units)} 个购买单位")
        
        # 为每个购买单位关联所有产品
        for unit in units:
            unit_id = unit[0]
            unit_name = unit[1]
            logger.info(f"为购买单位 {unit_name} (ID: {unit_id}) 创建产品关联")
            
            for product in products:
                product_id = product[0]
                product_name = product[2]
                product_price = product[3]
                
                # 检查是否已存在关联
                cursor.execute("SELECT id FROM customer_products WHERE unit_id = ? AND product_id = ?", (unit_id, product_id))
                if not cursor.fetchone():
                    # 创建关联，使用产品的原始价格作为自定义价格
                    cursor.execute("""
                        INSERT INTO customer_products (unit_id, product_id, custom_price, is_active)
                        VALUES (?, ?, ?, 1)
                    """, (unit_id, product_id, product_price))
                    
                    logger.debug(f"  - 关联产品: {product_name} (ID: {product_id})，价格: {product_price}")
        
        conn.commit()
        conn.close()
        
        logger.info("成功为所有购买单位关联产品")
        return True
    except Exception as e:
        logger.error(f"关联产品失败: {e}")
        return False

def check_associations():
    """检查关联情况"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查关联数量
        cursor.execute("SELECT COUNT(*) FROM customer_products WHERE is_active = 1")
        count = cursor.fetchone()[0]
        logger.info(f"总关联数量: {count}")
        
        # 按购买单位分组检查
        cursor.execute("""
            SELECT pu.unit_name, COUNT(cp.id) as product_count
            FROM purchase_units pu
            LEFT JOIN customer_products cp ON pu.id = cp.unit_id AND cp.is_active = 1
            WHERE pu.is_active = 1
            GROUP BY pu.id
        """)
        
        results = cursor.fetchall()
        logger.info("各购买单位产品关联情况:")
        for result in results:
            logger.info(f"  - {result[0]}: {result[1]} 个产品")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"检查关联失败: {e}")
        return False

if __name__ == "__main__":
    print("=== 创建购买单位产品关联 ===")
    
    # 创建表
    if create_customer_products_table():
        # 关联产品
        if associate_products_with_units():
            # 检查关联
            check_associations()
            print("\n✅ 操作完成！产品已成功与购买单位关联")
        else:
            print("\n❌ 关联产品失败")
    else:
        print("\n❌ 创建表失败")
