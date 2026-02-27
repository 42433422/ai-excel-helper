#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查Excel文件的实际结构
"""

import pandas as pd
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

excel_path = "templates\\尹玉华1 - 副本.xlsx"

def check_excel_structure():
    """检查Excel文件结构"""
    try:
        # 读取Sheet2工作表
        df = pd.read_excel(excel_path, sheet_name='Sheet2')
        logger.info(f"Sheet2 数据形状: {df.shape}")
        logger.info(f"Sheet2 列名: {df.columns.tolist()}")
        
        # 显示前5行数据
        logger.info("Sheet2 前5行数据:")
        print(df.head())
        
        # 如果有第3行有表头，尝试重新读取
        if len(df) > 0:
            df = pd.read_excel(excel_path, sheet_name='Sheet2', header=2)
            logger.info(f"使用第3行作为表头后的列名: {df.columns.tolist()}")
            logger.info("重新读取后的前5行数据:")
            print(df.head())
        
        return df
        
    except Exception as e:
        logger.error(f"检查Excel结构失败: {e}")
        return None

def main():
    """主函数"""
    print("=== 检查Excel文件结构 ===")
    df = check_excel_structure()
    
    if df is not None:
        print(f"\n✅ Excel结构检查完成！")

if __name__ == "__main__":
    main()
