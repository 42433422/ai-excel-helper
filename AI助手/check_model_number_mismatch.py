#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查产品型号是否匹配的问题
"""

import sqlite3
import pandas as pd
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

db_path = "products.db"
excel_path = "templates\\尹玉华1 - 副本.xlsx"

def check_database_ruixin_models():
    """检查数据库中蕊芯的产品型号"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取蕊芯家私和蕊芯家私1的产品型号
        cursor.execute("""
            SELECT pu.unit_name, p.model_number
            FROM customer_products cp
            JOIN products p ON cp.product_id = p.id
            JOIN purchase_units pu ON cp.unit_id = pu.id
            WHERE pu.unit_name LIKE '%蕊芯%' AND cp.is_active = 1
            ORDER BY pu.unit_name, p.model_number
        """)
        
        database_models = cursor.fetchall()
        conn.close()
        
        logger.info("数据库中的蕊芯产品型号:")
        ruixin_models = {}
        for unit_name, model in database_models:
            if unit_name not in ruixin_models:
                ruixin_models[unit_name] = []
            ruixin_models[unit_name].append(model)
        
        for unit_name, models in ruixin_models.items():
            logger.info(f"{unit_name} ({len(models)}个): {models}")
        
        return ruixin_models
        
    except Exception as e:
        logger.error(f"检查数据库型号失败: {e}")
        return {}

def check_excel_ruixin_models():
    """检查Excel文件中蕊芯的产品型号"""
    try:
        # 检查Sheet2
        df_sheet2 = pd.read_excel(excel_path, sheet_name='Sheet2')
        df_sheet2.columns = ['产品编号', '产品名称', '空列', '内部价格']
        
        excel_models = []
        for idx, row in df_sheet2.iterrows():
            code = str(row['产品编号']).strip()
            name = str(row['产品名称']).strip()
            
            if idx == 0 or pd.isna(code) or code in ['nan', '', 'None']:
                continue
                
            if code and name:
                excel_models.append(code)
        
        logger.info(f"Excel Sheet2中的产品型号 ({len(excel_models)}个): {excel_models}")
        
        # 检查净味系列报价工作表
        df_jingwei = pd.read_excel(excel_path, sheet_name='净味系列报价')
        jingwei_models = []
        
        # 手动查找编号列
        for idx, row in df_jingwei.iterrows():
            if idx == 0:  # 跳过表头行
                continue
            
            first_col = str(row.iloc[0]).strip()
            second_col = str(row.iloc[1]).strip()
            
            if first_col and first_col != 'nan' and first_col != '' and first_col != 'None':
                jingwei_models.append(first_col)
        
        logger.info(f"Excel 净味系列报价中的产品型号 ({len(jingwei_models)}个): {jingwei_models}")
        
        return {
            'sheet2': excel_models,
            'jingwei': jingwei_models
        }
        
    except Exception as e:
        logger.error(f"检查Excel型号失败: {e}")
        return {}

def compare_models():
    """比较数据库和Excel中的产品型号"""
    logger.info("\n=== 产品型号对比分析 ===")
    
    # 获取数据库中的型号
    db_models = check_database_ruixin_models()
    
    # 获取Excel中的型号
    excel_models = check_excel_ruixin_models()
    
    # 对比分析
    for unit_name, models in db_models.items():
        logger.info(f"\n{unit_name}:")
        logger.info(f"  数据库型号 ({len(models)}个): {models}")
        
        # 检查在Excel中是否存在
        missing_in_excel = []
        for model in models:
            if model not in excel_models['sheet2'] and model not in excel_models['jingwei']:
                missing_in_excel.append(model)
        
        if missing_in_excel:
            logger.info(f"  在Excel中缺失的型号 ({len(missing_in_excel)}个): {missing_in_excel}")
        else:
            logger.info(f"  ✅ 所有型号在Excel中都存在")

def main():
    """主函数"""
    print("=== 检查产品型号匹配问题 ===")
    compare_models()

if __name__ == "__main__":
    main()
