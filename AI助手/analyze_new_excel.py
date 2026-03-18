#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析新的Excel文件，找出所有购买单位和产品
"""

import pandas as pd
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

excel_path = "templates\\新建 XLSX 工作表 (2).xlsx"

def analyze_new_excel():
    """分析新Excel文件"""
    try:
        # 获取所有工作表名称
        xl_file = pd.ExcelFile(excel_path)
        sheet_names = xl_file.sheet_names
        logger.info(f"新Excel文件工作表: {sheet_names}")
        
        all_units = set()
        all_products = {}
        
        # 分析每个工作表
        for sheet_name in sheet_names:
            logger.info(f"\n=== 分析工作表: {sheet_name} ===")
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
            logger.info(f"工作表 {sheet_name} 行数: {len(df)}")
            logger.info(f"工作表 {sheet_name} 列数: {len(df.columns)}")
            logger.info(f"工作表 {sheet_name} 列名: {df.columns.tolist()}")
            
            # 显示前10行数据
            logger.info(f"工作表 {sheet_name} 前10行数据:")
            print(df.head(10))
            
            # 查找表头行
            header_row = None
            for i in range(min(5, len(df))):
                row = df.iloc[i]
                if any('公司' in str(cell) or '单位' in str(cell) for cell in row if pd.notna(cell)):
                    header_row = i
                    logger.info(f"找到可能的表头行在第{i+1}行")
                    break
            
            if header_row is not None:
                # 使用找到的行作为表头重新读取
                df = pd.read_excel(excel_path, sheet_name=sheet_name, header=header_row)
                logger.info(f"使用第{header_row+1}行作为表头，重新读取数据")
                logger.info(f"新列名: {df.columns.tolist()}")
                
                # 显示重新读取后的前10行
                logger.info("重新读取后的前10行数据:")
                print(df.head(10))
                
                # 查找公司/单位列和产品相关列
                unit_col = None
                for col in df.columns:
                    col_str = str(col)
                    if '公司' in col_str or '单位' in col_str or '客户' in col_str:
                        unit_col = col
                        logger.info(f"找到单位列: {unit_col}")
                        break
                
                if unit_col:
                    # 提取单位名称
                    units_in_sheet = df[unit_col].dropna().unique()
                    all_units.update(units_in_sheet)
                    logger.info(f"工作表 {sheet_name} 中的单位: {units_in_sheet.tolist()}")
                    
                    # 分析产品结构
                    product_cols = [col for col in df.columns if '产品' in str(col) or '型号' in str(col) or '名称' in str(col)]
                    logger.info(f"产品相关列: {product_cols}")
        
        logger.info(f"\n=== 汇总分析 ===")
        logger.info(f"所有发现的购买单位 ({len(all_units)} 个):")
        for unit in sorted(all_units):
            if pd.notna(unit) and str(unit).strip():
                logger.info(f"  - {unit}")
        
        return all_units, all_products
        
    except Exception as e:
        logger.error(f"分析新Excel文件失败: {e}")
        return set(), {}

def main():
    """主函数"""
    print("=== 分析新Excel文件中的购买单位和产品 ===")
    units, products = analyze_new_excel()
    print(f"\n新Excel文件中发现 {len(units)} 个购买单位")

if __name__ == "__main__":
    main()
