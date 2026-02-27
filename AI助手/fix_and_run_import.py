#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复并重新导入正确的27个产品
"""

import sqlite3
import pandas as pd
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

db_path = "products.db"
excel_path = "尹玉华1 - 副本.xlsx"

def clean_database():
    """清理数据库中的产品和关联数据"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 清理customer_products表
        cursor.execute("DELETE FROM customer_products")
        logger.info("清理了customer_products表")
        
        # 清理products表
        cursor.execute("DELETE FROM products")
        logger.info("清理了products表")
        
        # 重置自增计数器
        cursor.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name = 'products'")
        cursor.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name = 'customer_products'")
        
        conn.commit()
        conn.close()
        
        logger.info("数据库清理完成")
        return True
    except Exception as e:
        logger.error(f"清理数据库失败: {e}")
        return False

def import_sheet2_products():
    """从Sheet2工作表导入产品"""
    try:
        # 读取Sheet2工作表
        df = pd.read_excel(excel_path, sheet_name='Sheet2', header=None)
        logger.info(f"读取Sheet2工作表成功，共 {len(df)} 行数据")
        
        # 手动设置列名
        df.columns = ['产品编号', '产品名称', '规格', '内部价格', '空列', '外部价格']
        
        # 从第3行开始（跳过表头行和标题行）
        product_data = df.iloc[2:].copy()
        
        # 去重，保留第一次出现的产品
        seen_models = set()
        valid_products = []
        
        for idx, row in product_data.iterrows():
            code = str(row['产品编号']).strip()
            name = str(row['产品名称']).strip()
            
            # 跳过空值和无效行
            if code in ['nan', '', 'None'] or name in ['nan', '', 'None']:
                continue
            
            # 跳过表头行
            if code == '产品编号' or name == '产品名称':
                continue
            
            # 确保产品编号不为空且不是纯文本
            if code and code != 'nan' and len(code) > 0:
                # 去重
                if code not in seen_models:
                    seen_models.add(code)
                    
                    # 获取价格（内部价格）
                    internal_price = row['内部价格']
                    if pd.notna(internal_price) and isinstance(internal_price, (int, float)):
                        price = float(internal_price)
                    else:
                        price = 0.0
                    
                    valid_products.append((code, name, price))
        
        logger.info(f"去重后有 {len(valid_products)} 个唯一产品")
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        imported_count = 0
        for code, name, price in valid_products:
            # 插入产品
            cursor.execute("""
                INSERT INTO products (model_number, name, price, is_active, created_at, updated_at)
                VALUES (?, ?, ?, 1, datetime('now'), datetime('now'))
            """, (code, name, price))
            imported_count += 1
            logger.info(f"导入产品: {code} - {name} (价格: {price})")
        
        conn.commit()
        conn.close()
        
        logger.info(f"成功导入 {imported_count} 个产品")
        return imported_count
    except Exception as e:
        logger.error(f"导入产品失败: {e}")
        return 0

def recreate_customer_products():
    """重新创建购买单位和产品的关联"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取所有活跃购买单位
        cursor.execute("SELECT id, unit_name FROM purchase_units WHERE is_active = 1")
        units = cursor.fetchall()
        logger.info(f"找到 {len(units)} 个购买单位")
        
        # 获取所有活跃产品
        cursor.execute("SELECT id, model_number, name FROM products WHERE is_active = 1")
        products = cursor.fetchall()
        logger.info(f"找到 {len(products)} 个产品")
        
        # 为每个购买单位关联所有产品
        association_count = 0
        for unit in units:
            unit_id = unit[0]
            unit_name = unit[1]
            
            for product in products:
                product_id = product[0]
                
                # 插入关联 (修复：提供正确的3个绑定参数)
                cursor.execute("""
                    INSERT INTO customer_products (unit_id, product_id, custom_price, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, 1, datetime('now'), datetime('now'))
                """, (unit_id, product_id, 0.0))
                association_count += 1
        
        conn.commit()
        conn.close()
        
        logger.info(f"成功创建 {association_count} 个产品关联")
        return association_count
    except Exception as e:
        logger.error(f"创建关联失败: {e}")
        return 0

def verify_import():
    """验证导入结果"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查产品数量
        cursor.execute("SELECT COUNT(*) FROM products WHERE is_active = 1")
        product_count = cursor.fetchone()[0]
        logger.info(f"数据库中产品数量: {product_count}")
        
        # 检查关联数量
        cursor.execute("SELECT COUNT(*) FROM customer_products WHERE is_active = 1")
        association_count = cursor.fetchone()[0]
        logger.info(f"数据库中关联数量: {association_count}")
        
        # 检查购买单位数量
        cursor.execute("SELECT COUNT(*) FROM purchase_units WHERE is_active = 1")
        unit_count = cursor.fetchone()[0]
        logger.info(f"数据库中购买单位数量: {unit_count}")
        
        # 查看所有导入的产品
        cursor.execute("SELECT model_number, name, price FROM products WHERE is_active = 1 ORDER BY model_number")
        imported_products = cursor.fetchall()
        logger.info("所有导入的产品:")
        for model, name, price in imported_products:
            logger.info(f"  - {model}: {name} (价格: {price})")
        
        conn.close()
        
        return {
            'product_count': product_count,
            'association_count': association_count,
            'unit_count': unit_count
        }
    except Exception as e:
        logger.error(f"验证导入失败: {e}")
        return None

def main():
    """主函数"""
    print("=== 修复并导入正确的27个产品 ===")
    
    # 清理数据库
    if clean_database():
        # 导入产品
        imported_count = import_sheet2_products()
        if imported_count > 0:
            # 重新创建关联
            association_count = recreate_customer_products()
            if association_count > 0:
                # 验证导入
                result = verify_import()
                if result:
                    print(f"\n✅ 操作完成！")
                    print(f"导入产品数量: {result['product_count']}")
                    print(f"创建关联数量: {result['association_count']}")
                    print(f"购买单位数量: {result['unit_count']}")
                    return True
    
    print("\n❌ 操作失败！")
    return False

if __name__ == "__main__":
    main()
