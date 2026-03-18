#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从尹玉华1 - 副本.xlsx文件中提取蕊芯产品数据
"""

import sqlite3
import pandas as pd
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

db_path = "products.db"
excel_path = "templates\\尹玉华1 - 副本.xlsx"

def extract_ruixin1_from_sheet2():
    """从Sheet2提取蕊芯家私1的数据"""
    try:
        # 读取Sheet2
        df = pd.read_excel(excel_path, sheet_name='Sheet2')
        logger.info(f"Sheet2 数据形状: {df.shape}")
        
        # 手动设置列名
        df.columns = ['产品编号', '产品名称', '空列', '内部价格']
        
        # 从第2行开始（跳过表头行）
        product_data = df.iloc[1:].copy()
        
        ruixin1_products = []
        for idx, row in product_data.iterrows():
            code = str(row['产品编号']).strip()
            name = str(row['产品名称']).strip()
            internal_price = row['内部价格']
            
            # 跳过空值和无效行
            if pd.isna(code) or code in ['nan', '', 'None'] or pd.isna(name) or name in ['nan', '', 'None']:
                continue
            
            # 确保数据有效
            if code and name:
                internal_price_val = float(internal_price) if pd.notna(internal_price) and isinstance(internal_price, (int, float)) else 0.0
                
                ruixin1_products.append({
                    'model': code,
                    'name': name,
                    'price': internal_price_val
                })
        
        logger.info(f"从Sheet2提取到 {len(ruixin1_products)} 个蕊芯家私1产品")
        
        # 显示所有产品
        logger.info("蕊芯家私1产品列表:")
        for product in ruixin1_products:
            logger.info(f"  - {product['model']}: {product['name']} - ¥{product['price']}")
        
        return ruixin1_products
        
    except Exception as e:
        logger.error(f"提取蕊芯家私1数据失败: {e}")
        return []

def extract_ruixin_from_chuhuo():
    """从出货工作表提取蕊芯家私的数据"""
    try:
        # 读取出货工作表
        df = pd.read_excel(excel_path, sheet_name='出货')
        logger.info(f"出货工作表数据形状: {df.shape}")
        
        # 提取蕊芯的记录
        ruixin_records = df[df['24出货'].str.contains('蕊芯', na=False)]
        logger.info(f"找到 {len(ruixin_records)} 条蕊芯记录")
        
        # 提取产品型号和价格信息
        ruixin_products = {}
        
        for idx, row in ruixin_records.iterrows():
            model = str(row['产品型号']).strip()
            customer_price = row['客户单价']
            customer_amount = row['客户金额']
            
            # 跳过空值
            if pd.isna(model) or model == 'nan' or model == '':
                continue
            
            # 使用客户单价作为价格
            price = float(customer_price) if pd.notna(customer_price) else 0.0
            
            # 如果已经存在相同型号，使用最后一次出现的价格
            ruixin_products[model] = {
                'model': model,
                'name': model,  # 使用型号作为名称
                'price': price
            }
        
        ruixin_product_list = list(ruixin_products.values())
        logger.info(f"从出货工作表提取到 {len(ruixin_product_list)} 个蕊芯家私产品")
        
        # 显示前20个产品
        logger.info("蕊芯家私产品示例（前20个）:")
        for product in ruixin_product_list[:20]:
            logger.info(f"  - {product['model']}: {product['name']} - ¥{product['price']}")
        
        return ruixin_product_list
        
    except Exception as e:
        logger.error(f"提取蕊芯家私数据失败: {e}")
        return []

def update_ruixin_products(ruixin1_products, ruixin_products):
    """更新数据库中的蕊芯产品"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取蕊芯家私和蕊芯家私1的ID
        cursor.execute("SELECT id, unit_name FROM purchase_units WHERE unit_name LIKE '%蕊芯%' AND is_active = 1")
        ruixin_units = cursor.fetchall()
        
        ruixin1_id = None
        ruixin_id = None
        
        for unit_id, unit_name in ruixin_units:
            if '1' in unit_name:
                ruixin1_id = unit_id
            else:
                ruixin_id = unit_id
        
        logger.info(f"找到购买单位:")
        logger.info(f"  - 蕊芯家私1: ID {ruixin1_id}")
        logger.info(f"  - 蕊芯家私: ID {ruixin_id}")
        
        updated_count1 = 0
        updated_count = 0
        
        # 更新蕊芯家私1的价格
        if ruixin1_id and ruixin1_products:
            cursor.execute("""
                SELECT cp.id, p.model_number, cp.custom_price
                FROM customer_products cp
                JOIN products p ON cp.product_id = p.id
                WHERE cp.unit_id = ? AND cp.is_active = 1
            """, (ruixin1_id,))
            
            existing_products = cursor.fetchall()
            
            for product_id, model_number, current_price in existing_products:
                # 在新产品列表中查找对应产品
                for new_product in ruixin1_products:
                    if new_product['model'] == model_number:
                        new_price = new_product['price']
                        
                        cursor.execute("""
                            UPDATE customer_products 
                            SET custom_price = ?, updated_at = datetime('now')
                            WHERE id = ?
                        """, (new_price, product_id))
                        
                        updated_count1 += 1
                        logger.info(f"更新蕊芯家私1产品 {model_number}: ¥{current_price} -> ¥{new_price}")
                        break
        
        # 更新蕊芯家私的价格
        if ruixin_id and ruixin_products:
            cursor.execute("""
                SELECT cp.id, p.model_number, cp.custom_price
                FROM customer_products cp
                JOIN products p ON cp.product_id = p.id
                WHERE cp.unit_id = ? AND cp.is_active = 1
            """, (ruixin_id,))
            
            existing_products = cursor.fetchall()
            
            for product_id, model_number, current_price in existing_products:
                # 在新产品列表中查找对应产品
                for new_product in ruixin_products:
                    if new_product['model'] == model_number:
                        new_price = new_product['price']
                        
                        cursor.execute("""
                            UPDATE customer_products 
                            SET custom_price = ?, updated_at = datetime('now')
                            WHERE id = ?
                        """, (new_price, product_id))
                        
                        updated_count += 1
                        logger.info(f"更新蕊芯家私产品 {model_number}: ¥{current_price} -> ¥{new_price}")
                        break
        
        conn.commit()
        conn.close()
        
        logger.info(f"更新完成:")
        logger.info(f"  - 蕊芯家私1: 更新了 {updated_count1} 个产品价格")
        logger.info(f"  - 蕊芯家私: 更新了 {updated_count} 个产品价格")
        
        return updated_count1, updated_count
        
    except Exception as e:
        logger.error(f"更新蕊芯产品失败: {e}")
        return 0, 0

def verify_update():
    """验证更新结果"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取蕊芯家私和蕊芯家私1的产品和价格
        cursor.execute("""
            SELECT pu.unit_name, p.model_number, p.name, cp.custom_price
            FROM customer_products cp
            JOIN products p ON cp.product_id = p.id
            JOIN purchase_units pu ON cp.unit_id = pu.id
            WHERE pu.unit_name LIKE '%蕊芯%' AND cp.is_active = 1
            ORDER BY pu.unit_name, p.model_number
        """)
        
        products = cursor.fetchall()
        logger.info("更新后的蕊芯产品:")
        for unit_name, model, name, price in products:
            logger.info(f"  - {unit_name}: {model} - {name} - ¥{price}")
        
        conn.close()
        return len(products)
        
    except Exception as e:
        logger.error(f"验证更新失败: {e}")
        return 0

def main():
    """主函数"""
    print("=== 从尹玉华1 - 副本.xlsx提取蕊芯产品数据 ===")
    
    # 1. 从Sheet2提取蕊芯家私1的数据
    ruixin1_products = extract_ruixin1_from_sheet2()
    
    # 2. 从出货工作表提取蕊芯家私的数据
    ruixin_products = extract_ruixin_from_chuhuo()
    
    if ruixin1_products or ruixin_products:
        # 3. 更新数据库中的价格
        updated_count1, updated_count = update_ruixin_products(ruixin1_products, ruixin_products)
        
        # 4. 验证更新结果
        product_count = verify_update()
        
        print(f"\n✅ 从尹玉华文件提取和更新完成！")
        print(f"蕊芯家私1: 更新了 {updated_count1} 个产品价格")
        print(f"蕊芯家私: 更新了 {updated_count} 个产品价格")
        print(f"总共有 {product_count} 个蕊芯产品")
        return True
    else:
        print("\n❌ 未能提取到产品数据")
        return False

if __name__ == "__main__":
    main()
