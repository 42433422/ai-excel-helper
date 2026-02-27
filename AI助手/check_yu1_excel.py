#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查尹玉华1 - 副本.xlsx文件的工作表结构
"""

import pandas as pd
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

excel_path = "templates\\尹玉华1 - 副本.xlsx"

def check_yu1_excel():
    """检查尹玉华1 - 副本.xlsx文件"""
    try:
        # 获取所有工作表名称
        xl_file = pd.ExcelFile(excel_path)
        sheet_names = xl_file.sheet_names
        logger.info(f"工作表列表: {sheet_names}")
        
        # 分析每个工作表
        for sheet_name in sheet_names:
            logger.info(f"\n=== 分析工作表: {sheet_name} ===")
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
            logger.info(f"数据形状: {df.shape}")
            logger.info(f"列名: {df.columns.tolist()}")
            
            # 显示前10行数据
            logger.info("前10行数据:")
            print(df.head(10))
            
            # 检查是否包含蕊芯数据
            if any('蕊芯' in str(cell) for col in df.columns for cell in df[col].dropna() if pd.notna(cell)):
                logger.info("找到蕊芯相关数据！")
            
            if any('购买单位' in str(col) for col in df.columns):
                logger.info("找到购买单位列！")
                # 查找购买单位列
                for col in df.columns:
                    if '购买单位' in str(col):
                        units = df[col].dropna().unique()
                        logger.info(f"购买单位: {units}")
                        ruixin_units = [u for u in units if '蕊芯' in str(u)]
                        if ruixin_units:
                            logger.info(f"找到蕊芯相关单位: {ruixin_units}")
        
        return sheet_names
        
    except Exception as e:
        logger.error(f"检查Excel失败: {e}")
        return []

def main():
    """主函数"""
    print("=== 检查尹玉华1 - 副本.xlsx文件 ===")
    sheet_names = check_yu1_excel()
    
    if sheet_names:
        print(f"\n✅ 检查完成！工作表: {sheet_names}")

if __name__ == "__main__":
    main()
