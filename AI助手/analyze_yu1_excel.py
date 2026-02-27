#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析尹玉华1 - 副本.xlsx文件中的数据
"""

import pandas as pd
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

excel_path = "templates\\尹玉华1 - 副本.xlsx"

def analyze_yu1_excel():
    """分析尹玉华1 - 副本.xlsx文件"""
    try:
        # 读取Sheet1
        df1 = pd.read_excel(excel_path, sheet_name='Sheet1')
        logger.info(f"Sheet1 数据形状: {df1.shape}")
        logger.info(f"Sheet1 列名: {df1.columns.tolist()}")
        logger.info("Sheet1 前10行数据:")
        print(df1.head(10))
        
        # 读取Sheet2
        df2 = pd.read_excel(excel_path, sheet_name='Sheet2')
        logger.info(f"\nSheet2 数据形状: {df2.shape}")
        logger.info(f"Sheet2 列名: {df2.columns.tolist()}")
        logger.info("Sheet2 前10行数据:")
        print(df2.head(10))
        
        # 检查是否有蕊芯相关的数据
        if 'Sheet1' in df1.columns or 'Sheet2' in df2.columns:
            logger.info("\n检查Sheet1中是否包含蕊芯相关数据:")
            for col in df1.columns:
                if '购买单位' in str(col) or '单位' in str(col):
                    units = df1[col].dropna().unique()
                    ruixin_units = [u for u in units if '蕊芯' in str(u)]
                    if ruixin_units:
                        logger.info(f"找到蕊芯相关单位: {ruixin_units}")
        
        return df1, df2
        
    except Exception as e:
        logger.error(f"分析Excel失败: {e}")
        return None, None

def main():
    """主函数"""
    print("=== 分析尹玉华1 - 副本.xlsx文件 ===")
    df1, df2 = analyze_yu1_excel()
    
    if df1 is not None and df2 is not None:
        print(f"\n✅ 分析完成！")

if __name__ == "__main__":
    main()
