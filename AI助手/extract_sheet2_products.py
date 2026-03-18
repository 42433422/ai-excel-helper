#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接解析Sheet2工作表，提取真正的产品列表
"""

import pandas as pd
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

excel_path = "尹玉华1 - 副本.xlsx"

def extract_sheet2_products():
    """提取Sheet2中的产品列表"""
    try:
        # 读取Sheet2工作表
        df = pd.read_excel(excel_path, sheet_name='Sheet2', header=None)
        logger.info(f"Sheet2 工作表行数: {len(df)}")
        
        # 显示所有数据
        logger.info("Sheet2 所有数据:")
        print(df)
        
        # 手动设置列名
        df.columns = ['产品编号', '产品名称', '规格', '内部价格', '空列', '外部价格']
        
        # 从第2行开始（跳过表头）
        product_data = df.iloc[1:].copy()
        
        # 过滤掉空值和无效行
        valid_products = []
        for idx, row in product_data.iterrows():
            code = str(row['产品编号']).strip()
            name = str(row['产品名称']).strip()
            
            # 跳过空值和无效行
            if code in ['nan', '', 'None'] or name in ['nan', '', 'None']:
                continue
            
            # 确保产品编号不为空且不是纯文本
            if code and code != 'nan' and len(code) > 0:
                valid_products.append((code, name))
        
        logger.info(f"找到 {len(valid_products)} 个有效产品")
        
        # 显示所有有效产品
        logger.info("所有有效产品:")
        for i, (code, name) in enumerate(valid_products):
            logger.info(f"  {i+1}. {code}: {name}")
        
        return valid_products
        
    except Exception as e:
        logger.error(f"提取产品失败: {e}")
        return []

def main():
    """主函数"""
    print("=== 提取Sheet2产品列表 ===")
    products = extract_sheet2_products()
    print(f"\nSheet2中真正产品数量: {len(products)}")

if __name__ == "__main__":
    main()
