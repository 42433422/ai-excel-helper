#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析新Excel文件的结构，为按购买单位分类导入做准备
"""

import pandas as pd
import logging
from collections import defaultdict

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

excel_path = "templates\\新建 XLSX 工作表 (2).xlsx"

def analyze_excel_structure():
    """分析Excel文件结构"""
    try:
        # 读取Sheet1
        df = pd.read_excel(excel_path, sheet_name='Sheet1')
        logger.info(f"Excel数据形状: {df.shape}")
        logger.info(f"列名: {df.columns.tolist()}")
        
        # 显示前10行数据
        logger.info("前10行数据:")
        print(df.head(10))
        
        # 获取所有购买单位
        units = df['购买单位'].dropna().unique()
        logger.info(f"\n购买单位列表 ({len(units)} 个):")
        for i, unit in enumerate(units, 1):
            logger.info(f"  {i}. {unit}")
        
        # 按购买单位统计产品数量
        unit_stats = {}
        for unit in units:
            unit_data = df[df['购买单位'] == unit]
            product_count = len(unit_data)
            unit_stats[unit] = product_count
        
        logger.info(f"\n各购买单位产品统计:")
        for unit, count in sorted(unit_stats.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {unit}: {count} 个产品")
        
        # 分析产品重复情况
        logger.info(f"\n分析产品重复情况:")
        
        # 按购买单位分组分析
        for unit in units:
            unit_data = df[df['购买单位'] == unit]
            models = unit_data['产品型号'].value_counts()
            duplicates = models[models > 1]
            
            if len(duplicates) > 0:
                logger.info(f"\n{unit} 中的重复产品型号:")
                for model, count in duplicates.head(10).items():
                    model_data = unit_data[unit_data['产品型号'] == model]
                    logger.info(f"  - {model}: {count} 次出现")
                    # 显示该产品的不同名称
                    names = model_data['产品名称'].unique()
                    if len(names) > 1:
                        logger.info(f"    不同名称: {names}")
        
        # 分析日期型号
        logger.info(f"\n分析日期型号:")
        date_models = df[df['产品型号'].str.contains(r'\d{6}', na=False)]['产品型号'].value_counts()
        date_duplicates = date_models[date_models > 1]
        
        if len(date_duplicates) > 0:
            logger.info(f"重复的日期型号 ({len(date_duplicates)} 个):")
            for model, count in date_duplicates.head(10).items():
                logger.info(f"  - {model}: {count} 次出现")
        
        return df, units, unit_stats
        
    except Exception as e:
        logger.error(f"分析Excel失败: {e}")
        return None, [], {}

def main():
    """主函数"""
    print("=== 分析新Excel文件结构 ===")
    df, units, unit_stats = analyze_excel_structure()
    
    if df is not None:
        print(f"\n✅ 分析完成！")
        print(f"数据行数: {len(df)}")
        print(f"购买单位: {len(units)} 个")
        print(f"总产品: {len(df)} 条记录")

if __name__ == "__main__":
    main()
