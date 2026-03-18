#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更详细地分析Excel文件，找出真正的产品列表
"""

import pandas as pd
import numpy as np
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

excel_path = "尹玉华1 - 副本.xlsx"

def analyze_excel_structure():
    """详细分析Excel文件结构"""
    try:
        # 获取所有工作表名称
        xl_file = pd.ExcelFile(excel_path)
        sheet_names = xl_file.sheet_names
        logger.info(f"Excel文件工作表: {sheet_names}")
        
        # 检查每个工作表
        for sheet_name in sheet_names:
            logger.info(f"\n=== 分析工作表: {sheet_name} ===")
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
            logger.info(f"工作表 {sheet_name} 行数: {len(df)}")
            logger.info(f"工作表 {sheet_name} 列数: {len(df.columns)}")
            
            # 打印前5行数据
            logger.info(f"工作表 {sheet_name} 前5行数据:")
            print(df.head())
            
            # 查找可能的表头行
            for i in range(min(5, len(df))):
                row = df.iloc[i]
                if any('产品型号' in str(cell) for cell in row if pd.notna(cell)):
                    logger.info(f"找到可能的表头行在第{i+1}行")
                    # 使用这一行作为表头重新读取
                    df = pd.read_excel(excel_path, sheet_name=sheet_name, header=i)
                    logger.info(f"使用第{i+1}行作为表头，重新读取数据")
                    logger.info(f"新列名: {df.columns.tolist()}")
                    break
            
            # 检查是否包含产品型号列
            if '产品型号' in df.columns:
                # 过滤掉空值
                product_data = df[['产品型号', '产品名称']].dropna()
                logger.info(f"过滤后有 {len(product_data)} 行产品数据")
                
                # 查看前10行产品数据
                logger.info("前10行产品数据:")
                for idx, row in product_data.head(10).iterrows():
                    logger.info(f"  {idx}: {row['产品型号']} - {row['产品名称']}")
                
                # 去重并统计
                unique_products = product_data.drop_duplicates(subset=['产品型号'])
                logger.info(f"去重后有 {len(unique_products)} 个唯一产品")
                
                # 打印所有唯一产品
                logger.info("所有唯一产品:")
                for idx, row in unique_products.iterrows():
                    logger.info(f"  - {row['产品型号']}: {row['产品名称']}")
            else:
                logger.info("未找到产品型号列")
        
        return True
    except Exception as e:
        logger.error(f"分析Excel文件失败: {e}")
        return False

def main():
    """主函数"""
    print("=== 详细分析Excel文件结构 ===")
    analyze_excel_structure()

if __name__ == "__main__":
    main()
