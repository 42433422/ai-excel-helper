#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按照尹玉华1 - 副本.xlsx文件重新导入蕊芯产品数据
"""

import sqlite3
import pandas as pd
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

db_path = "products.db"
excel_path = "templates\\尹玉华1 - 副本.xlsx"
new_excel_path = "templates\\新建 XLSX 工作表 (2).xlsx"

def clean_ruixin_units():
    """清理蕊芯相关的单位和产品"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取蕊芯相关单位
        cursor.execute("SELECT id FROM purchase_units WHERE unit_name LIKE '%蕊芯%'")
        ruixin_units = cursor.fetchall()
        
        for unit_id, in ruixin_units:
            # 删除该单位的产品关联
            cursor.execute("DELETE FROM customer_products WHERE unit_id = ?", (unit_id,))
            # 删除该单位
            cursor.execute("DELETE FROM purchase_units WHERE id = ?", (unit_id,))
        
        conn.commit()
        conn.close()
        logger.info(f"清理了 {len(ruixin_units)} 个蕊芯相关单位")
        return True
    except Exception as e:
        logger.error(f"清理蕊芯单位失败: {e}")
        return False

def get_ruixin_products_from_yu1():
    """从尹玉华1文件获取蕊芯产品数据"""
    try:
        # 从Sheet2获取蕊芯家私1的数据
        df_sheet2 = pd.read_excel(excel_path, sheet_name='Sheet2')
        df_sheet2.columns = ['产品编号', '产品名称', '空列', '内部价格']
        
        ruixin1_products = []
        for idx, row in df_sheet2.iterrows():
            code = str(row['产品编号']).strip()
            name = str(row['产品名称']).strip()
            internal_price = row['内部价格']
            
            if idx == 0 or pd.isna(code) or code in ['nan', '', 'None']:
                continue
            
            if code and name:
                internal_price_val = float(internal_price) if pd.notna(internal_price) else 0.0
                ruixin1_products.append({
                    'model': code,
                    'name': name,
                    'internal_price': internal_price_val
                })
        
        logger.info(f"从Sheet2提取到 {len(ruixin1_products)} 个蕊芯家私1产品")
        
        # 从净味系列报价获取蕊芯家私的数据
        df_jingwei = pd.read_excel(excel_path, sheet_name='净味系列报价')
        
        ruixin_products = []
        for idx, row in df_jingwei.iterrows():
            if idx == 0:  # 跳过表头行
                continue
            
            first_col = str(row.iloc[0]).strip()
            second_col = str(row.iloc[1]).strip()
            third_col = str(row.iloc[2]).strip()
            fourth_col = str(row.iloc[3]).strip()  # 内单价
            fifth_col = str(row.iloc[4]).strip()   # 外单价
            
            if first_col and first_col != 'nan' and first_col != '' and first_col != 'None':
                # 获取内价和外价
                internal_price = float(fourth_col) if fourth_col and fourth_col != 'nan' and fourth_col != '' else 0.0
                external_price = float(fifth_col) if fifth_col and fifth_col != 'nan' and fifth_col != '' else internal_price
                
                ruixin_products.append({
                    'model': first_col,
                    'name': second_col,
                    'internal_price': internal_price,
                    'external_price': external_price
                })
        
        logger.info(f"从净味系列报价提取到 {len(ruixin_products)} 个蕊芯家私产品")
        
        return ruixin1_products, ruixin_products
        
    except Exception as e:
        logger.error(f"从尹玉华文件提取数据失败: {e}")
        return [], []

def import_ruixin_from_yu1():
    """从尹玉华1文件重新导入蕊芯数据"""
    try:
        # 1. 清理现有的蕊芯数据
        if not clean_ruixin_units():
            return False
        
        # 2. 获取新的产品数据
        ruixin1_products, ruixin_products = get_ruixin_products_from_yu1()
        
        if not ruixin1_products and not ruixin_products:
            logger.error("未能提取到产品数据")
            return False
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 3. 添加购买单位
        cursor.execute("""
            INSERT INTO purchase_units (unit_name, is_active, created_at, updated_at)
            VALUES (?, 1, datetime('now'), datetime('now'))
        """, ("蕊芯家私1",))
        ruixin1_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO purchase_units (unit_name, is_active, created_at, updated_at)
            VALUES (?, 1, datetime('now'), datetime('now'))
        """, ("蕊芯家私",))
        ruixin_id = cursor.lastrowid
        
        logger.info(f"创建购买单位: 蕊芯家私1 (ID: {ruixin1_id}), 蕊芯家私 (ID: {ruixin_id})")
        
        # 4. 添加产品
        product_ids = {}
        
        # 导入所有产品（避免重复）
        all_products = {}
        
        # 添加蕊芯家私1的产品
        for product in ruixin1_products:
            key = f"{product['model']}_{product['name']}"
            if key not in all_products:
                all_products[key] = {
                    'model': product['model'],
                    'name': product['name'],
                    'price': product['internal_price']  # 蕊芯家私1用内价
                }
        
        # 添加蕊芯家私的产品
        for product in ruixin_products:
            key = f"{product['model']}_{product['name']}"
            if key not in all_products:
                all_products[key] = {
                    'model': product['model'],
                    'name': product['name'],
                    'price': product['external_price']  # 蕊芯家私用外价
                }
        
        # 插入产品到数据库
        for product in all_products.values():
            cursor.execute("""
                INSERT INTO products (model_number, name, price, is_active, created_at, updated_at)
                VALUES (?, ?, ?, 1, datetime('now'), datetime('now'))
            """, (product['model'], product['name'], product['price']))
            product_ids[product['model']] = cursor.lastrowid
        
        # 5. 创建关联
        # 为蕊芯家私1创建关联（用内价）
        for product in ruixin1_products:
            if product['model'] in product_ids:
                cursor.execute("""
                    INSERT INTO customer_products (unit_id, product_id, custom_price, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, 1, datetime('now'), datetime('now'))
                """, (ruixin1_id, product_ids[product['model']], product['internal_price']))
        
        # 为蕊芯家私创建关联（用外价）
        for product in ruixin_products:
            if product['model'] in product_ids:
                cursor.execute("""
                    INSERT INTO customer_products (unit_id, product_id, custom_price, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, 1, datetime('now'), datetime('now'))
                """, (ruixin_id, product_ids[product['model']], product['external_price']))
        
        conn.commit()
        conn.close()
        
        logger.info(f"成功导入 {len(all_products)} 个产品")
        logger.info(f"蕊芯家私1: {len(ruixin1_products)} 个产品")
        logger.info(f"蕊芯家私: {len(ruixin_products)} 个产品")
        
        return True
        
    except Exception as e:
        logger.error(f"导入蕊芯数据失败: {e}")
        return False

def verify_import():
    """验证导入结果"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取蕊芯产品
        cursor.execute("""
            SELECT pu.unit_name, p.model_number, p.name, cp.custom_price
            FROM customer_products cp
            JOIN products p ON cp.product_id = p.id
            JOIN purchase_units pu ON cp.unit_id = pu.id
            WHERE pu.unit_name LIKE '%蕊芯%' AND cp.is_active = 1
            ORDER BY pu.unit_name, p.model_number
        """)
        
        products = cursor.fetchall()
        conn.close()
        
        logger.info("重新导入后的蕊芯产品:")
        for unit_name, model, name, price in products:
            logger.info(f"  - {unit_name}: {model} - {name} - ¥{price}")
        
        return len(products)
        
    except Exception as e:
        logger.error(f"验证导入失败: {e}")
        return 0

def main():
    """主函数"""
    print("=== 按照尹玉华1 - 副本.xlsx文件重新导入蕊芯数据 ===")
    
    if import_ruixin_from_yu1():
        product_count = verify_import()
        
        print(f"\n✅ 重新导入完成！")
        print(f"共有 {product_count} 个蕊芯产品")
        print("产品型号现在与Excel文件完全匹配")
        return True
    else:
        print("\n❌ 导入失败！")
        return False

if __name__ == "__main__":
    main()
