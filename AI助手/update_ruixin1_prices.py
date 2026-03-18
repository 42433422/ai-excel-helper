#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新蕊芯家私1的价格数据
"""

import sqlite3
import pandas as pd
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

db_path = "products.db"
excel_path = "templates\\尹玉华1 - 副本.xlsx"

def get_ruixin1_prices():
    """从Excel文件获取蕊芯家私1的价格数据"""
    try:
        # 读取Sheet2工作表
        df = pd.read_excel(excel_path, sheet_name='Sheet2', header=None)
        logger.info(f"读取Sheet2数据成功，共 {len(df)} 行")
        
        # 手动设置列名
        df.columns = ['产品编号', '产品名称', '规格', '内部价格', '空列', '外部价格']
        
        # 从第3行开始（跳过表头行和标题行）
        product_data = df.iloc[2:].copy()
        
        # 提取产品数据
        ruixin1_prices = {}
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
                
                # 蕊芯家私1使用内部价格
                ruixin1_prices[code] = {
                    'name': name,
                    'price': internal_price_val
                }
        
        logger.info(f"从Excel提取到 {len(ruixin1_prices)} 个蕊芯家私1产品")
        
        # 显示前10个产品作为示例
        logger.info("蕊芯家私1产品价格示例:")
        for i, (code, data) in enumerate(list(ruixin1_prices.items())[:10]):
            logger.info(f"  - {code}: {data['name']} - ¥{data['price']}")
        
        return ruixin1_prices
        
    except Exception as e:
        logger.error(f"提取蕊芯家私1价格失败: {e}")
        return {}

def update_ruixin1_prices(ruixin1_prices):
    """更新数据库中蕊芯家私1的价格"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取蕊芯家私1的ID
        cursor.execute("SELECT id FROM purchase_units WHERE unit_name = '蕊芯家私1' AND is_active = 1")
        ruixin1_unit = cursor.fetchone()
        
        if not ruixin1_unit:
            logger.error("找不到蕊芯家私1购买单位")
            return False
        
        ruixin1_id = ruixin1_unit[0]
        logger.info(f"找到蕊芯家私1购买单位，ID: {ruixin1_id}")
        
        # 获取蕊芯家私1现有的产品关联
        cursor.execute("""
            SELECT cp.id, p.model_number, cp.custom_price
            FROM customer_products cp
            JOIN products p ON cp.product_id = p.id
            WHERE cp.unit_id = ? AND cp.is_active = 1
        """, (ruixin1_id,))
        
        existing_products = cursor.fetchall()
        logger.info(f"蕊芯家私1现有 {len(existing_products)} 个产品关联")
        
        updated_count = 0
        
        # 更新价格
        for product_id, model_number, current_price in existing_products:
            if model_number in ruixin1_prices:
                new_price = ruixin1_prices[model_number]['price']
                
                if abs(new_price - current_price) > 0.001:  # 如果价格有变化
                    cursor.execute("""
                        UPDATE customer_products 
                        SET custom_price = ?, updated_at = datetime('now')
                        WHERE id = ?
                    """, (new_price, product_id))
                    
                    updated_count += 1
                    logger.info(f"更新产品 {model_number}: ¥{current_price} -> ¥{new_price}")
        
        conn.commit()
        conn.close()
        
        logger.info(f"成功更新 {updated_count} 个产品的价格")
        return updated_count
        
    except Exception as e:
        logger.error(f"更新价格失败: {e}")
        return 0

def verify_update():
    """验证更新结果"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取蕊芯家私1的产品和价格
        cursor.execute("""
            SELECT p.model_number, p.name, cp.custom_price
            FROM customer_products cp
            JOIN products p ON cp.product_id = p.id
            JOIN purchase_units pu ON cp.unit_id = pu.id
            WHERE pu.unit_name = '蕊芯家私1' AND cp.is_active = 1
            ORDER BY p.model_number
        """)
        
        products = cursor.fetchall()
        logger.info("蕊芯家私1更新后的产品价格:")
        for model, name, price in products:
            logger.info(f"  - {model}: {name} - ¥{price}")
        
        # 对比蕊芯家私的价格
        cursor.execute("""
            SELECT p.model_number, p.name, cp.custom_price
            FROM customer_products cp
            JOIN products p ON cp.product_id = p.id
            JOIN purchase_units pu ON cp.unit_id = pu.id
            WHERE pu.unit_name = '蕊芯家私' AND cp.is_active = 1
            ORDER BY p.model_number
        """)
        
        ruixin_products = cursor.fetchall()
        logger.info("蕊芯家私产品价格对比:")
        for model, name, price in ruixin_products[:5]:  # 只显示前5个
            logger.info(f"  - {model}: {name} - ¥{price}")
        
        conn.close()
        return len(products)
        
    except Exception as e:
        logger.error(f"验证更新失败: {e}")
        return 0

def main():
    """主函数"""
    print("=== 更新蕊芯家私1的价格数据 ===")
    
    # 1. 从Excel获取蕊芯家私1的价格数据
    ruixin1_prices = get_ruixin1_prices()
    
    if ruixin1_prices:
        # 2. 更新数据库中的价格
        updated_count = update_ruixin1_prices(ruixin1_prices)
        
        if updated_count > 0:
            # 3. 验证更新结果
            product_count = verify_update()
            
            print(f"\n✅ 价格更新完成！")
            print(f"更新了 {updated_count} 个产品的价格")
            print(f"蕊芯家私1共有 {product_count} 个产品")
            return True
        else:
            print("\n⚠️  没有价格需要更新")
            return False
    else:
        print("\n❌ 无法获取价格数据")
        return False

if __name__ == "__main__":
    main()
