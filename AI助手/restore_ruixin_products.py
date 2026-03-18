#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
恢复蕊芯家私和蕊芯家私1的产品数据
"""

import sqlite3
import pandas as pd
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

db_path = "products.db"
excel_path = "尹玉华1 - 副本.xlsx"  # 原来的Excel文件

def restore_ruixin_products():
    """恢复蕊芯家私和蕊芯家私1的产品数据"""
    try:
        # 读取原来的Sheet2工作表
        df = pd.read_excel(excel_path, sheet_name='Sheet2', header=None)
        logger.info(f"读取Sheet2数据成功，共 {len(df)} 行")
        
        # 手动设置列名
        df.columns = ['产品编号', '产品名称', '规格', '内部价格', '空列', '外部价格']
        
        # 从第3行开始（跳过表头行和标题行）
        product_data = df.iloc[2:].copy()
        
        # 提取产品数据
        ruixin_products = []
        for idx, row in product_data.iterrows():
            code = str(row['产品编号']).strip()
            name = str(row['产品名称']).strip()
            internal_price = row['内部价格']
            external_price = row['外部价格']
            
            # 跳过空值和无效行
            if code in ['nan', '', 'None'] or name in ['nan', '', 'None']:
                continue
            
            # 跳过表头行
            if code == '产品编号' or name == '产品名称':
                continue
            
            # 确保数据有效
            if code and code != 'nan' and len(code) > 0:
                internal_price_val = float(internal_price) if pd.notna(internal_price) and isinstance(internal_price, (int, float)) else 0.0
                external_price_val = float(external_price) if pd.notna(external_price) and isinstance(external_price, (int, float)) else 0.0
                
                ruixin_products.append({
                    'model': code,
                    'name': name,
                    'internal_price': internal_price_val,
                    'external_price': external_price_val
                })
        
        logger.info(f"从Sheet2提取到 {len(ruixin_products)} 个蕊芯产品")
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取蕊芯家私和蕊芯家私1的ID
        cursor.execute("SELECT id, unit_name FROM purchase_units WHERE unit_name LIKE '%蕊芯%'")
        ruixin_units = cursor.fetchall()
        
        if not ruixin_units:
            logger.error("找不到蕊芯家私和蕊芯家私1购买单位")
            return False
        
        # 导入产品（如果不存在）
        existing_products = set()
        cursor.execute("SELECT model_number FROM products WHERE is_active = 1")
        for row in cursor.fetchall():
            existing_products.add(row[0])
        
        imported_products = []
        for product in ruixin_products:
            model = product['model']
            name = product['name']
            if model not in existing_products:
                cursor.execute("""
                    INSERT INTO products (model_number, name, price, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, 1, datetime('now'), datetime('now'))
                """, (model, name, product['internal_price']))
                imported_products.append({'model': model, 'name': name})
        
        conn.commit()
        
        # 为每个蕊芯单位创建产品关联
        for unit_id, unit_name in ruixin_units:
            logger.info(f"为购买单位 '{unit_name}' (ID: {unit_id}) 创建产品关联")
            
            for product in ruixin_products:
                model = product['model']
                name = product['name']
                
                # 获取产品ID
                cursor.execute("SELECT id FROM products WHERE model_number = ?", (model,))
                product_row = cursor.fetchone()
                
                if product_row:
                    product_id = product_row[0]
                    
                    # 根据单位名称选择价格
                    if '1' in unit_name:  # 蕊芯家私1 使用内价
                        price = product['internal_price']
                    else:  # 蕊芯家私 使用外价
                        price = product['external_price']
                    
                    # 插入关联
                    cursor.execute("""
                        INSERT INTO customer_products (unit_id, product_id, custom_price, is_active, created_at, updated_at)
                        VALUES (?, ?, ?, 1, datetime('now'), datetime('now'))
                    """, (unit_id, product_id, price))
        
        conn.commit()
        conn.close()
        
        logger.info(f"恢复完成: 导入 {len(imported_products)} 个新产品，创建了 {len(ruixin_products) * 2} 个关联")
        return True
        
    except Exception as e:
        logger.error(f"恢复蕊芯产品失败: {e}")
        return False

def verify_restoration():
    """验证恢复结果"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查各购买单位的产品数量
        cursor.execute("""
            SELECT pu.unit_name, COUNT(cp.id) as product_count
            FROM purchase_units pu
            LEFT JOIN customer_products cp ON pu.id = cp.unit_id AND cp.is_active = 1
            WHERE pu.is_active = 1
            GROUP BY pu.id, pu.unit_name
            ORDER BY product_count DESC
        """)
        
        results = cursor.fetchall()
        logger.info("恢复后各购买单位产品数量:")
        for unit_name, count in results:
            logger.info(f"  - {unit_name}: {count} 个产品")
        
        # 检查蕊芯家私和蕊芯家私1的产品
        cursor.execute("""
            SELECT pu.unit_name, p.model_number, p.name, cp.custom_price
            FROM customer_products cp
            JOIN products p ON cp.product_id = p.id
            JOIN purchase_units pu ON cp.unit_id = pu.id
            WHERE pu.unit_name LIKE '%蕊芯%'
            ORDER BY pu.unit_name, p.model_number
        """)
        
        ruixin_products = cursor.fetchall()
        logger.info("蕊芯家私产品:")
        for unit_name, model, name, price in ruixin_products[:10]:  # 只显示前10个
            logger.info(f"  - {unit_name}: {model} - {name} - ¥{price}")
        
        conn.close()
        
        return True
    except Exception as e:
        logger.error(f"验证恢复失败: {e}")
        return False

def main():
    """主函数"""
    print("=== 恢复蕊芯家私和蕊芯家私1的产品数据 ===")
    
    # 恢复产品
    if restore_ruixin_products():
        # 验证恢复结果
        if verify_restoration():
            print("\n✅ 蕊芯产品恢复成功！")
        else:
            print("\n❌ 验证失败！")
    else:
        print("\n❌ 恢复失败！")

if __name__ == "__main__":
    main()
