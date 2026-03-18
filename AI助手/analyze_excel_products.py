#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细分析Excel文件中的产品数据
"""

import pandas as pd
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

excel_path = "尹玉华1 - 副本.xlsx"

def analyze_excel_products():
    """分析Excel文件中的产品数据"""
    try:
        # 读取Excel文件，使用第二行作为列标题
        df = pd.read_excel(excel_path, header=1)
        logger.info(f"读取Excel文件成功，共 {len(df)} 行数据")
        
        # 提取产品型号和名称列
        model_col = '产品型号'
        name_col = '产品名称'
        
        # 过滤掉空值
        product_data = df[[model_col, name_col]].dropna()
        logger.info(f"过滤后有 {len(product_data)} 行产品数据")
        
        # 去重，确保每个产品型号只计算一次
        unique_products = product_data.drop_duplicates(subset=[model_col])
        logger.info(f"去重后有 {len(unique_products)} 个唯一产品")
        
        # 打印所有唯一产品
        logger.info("所有唯一产品:")
        for _, row in unique_products.iterrows():
            model_number = row[model_col]
            product_name = row[name_col]
            logger.info(f"  - {model_number}: {product_name}")
        
        # 统计产品型号类型
        model_types = []
        for _, row in unique_products.iterrows():
            model_number = str(row[model_col])
            if '-' in model_number:
                model_types.append('带连字符')
            elif any(char.isalpha() for char in model_number):
                model_types.append('字母数字组合')
            else:
                model_types.append('纯数字')
        
        # 统计类型分布
        from collections import Counter
        type_counter = Counter(model_types)
        logger.info(f"产品型号类型分布: {type_counter}")
        
        return len(unique_products)
    except Exception as e:
        logger.error(f"分析Excel文件失败: {e}")
        return 0

def main():
    """主函数"""
    print("=== 详细分析Excel文件产品数据 ===")
    unique_count = analyze_excel_products()
    print(f"\nExcel文件中唯一产品型号数量: {unique_count}")

if __name__ == "__main__":
    main()
