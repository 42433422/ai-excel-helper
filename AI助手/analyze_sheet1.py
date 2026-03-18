#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析Sheet1中的购买单位和产品数据
"""

import pandas as pd
import logging
from collections import defaultdict

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

excel_path = "templates\\新建 XLSX 工作表 (2).xlsx"

def analyze_sheet1():
    """分析Sheet1中的数据"""
    try:
        # 读取Sheet1
        df = pd.read_excel(excel_path, sheet_name='Sheet1')
        logger.info(f"Sheet1 数据形状: {df.shape}")
        logger.info(f"列名: {df.columns.tolist()}")
        
        # 显示前10行数据
        logger.info("Sheet1 前10行数据:")
        print(df.head(10))
        
        # 提取购买单位
        units = df['购买单位'].dropna().unique()
        logger.info(f"发现的购买单位 ({len(units)} 个):")
        for unit in units:
            logger.info(f"  - {unit}")
        
        # 按购买单位分组统计产品
        unit_products = defaultdict(list)
        unit_product_counts = {}
        
        for unit in units:
            unit_data = df[df['购买单位'] == unit]
            product_models = unit_data['产品型号'].dropna().unique()
            unit_products[unit] = list(product_models)
            unit_product_counts[unit] = len(product_models)
        
        logger.info(f"\n各购买单位产品数量统计:")
        for unit, count in unit_product_counts.items():
            logger.info(f"  - {unit}: {count} 个产品")
        
        # 获取所有唯一的产品型号（跨所有购买单位）
        all_models = df['产品型号'].dropna().unique()
        logger.info(f"\n所有唯一产品型号 ({len(all_models)} 个):")
        for i, model in enumerate(sorted(all_models)):
            if i < 20:  # 只显示前20个
                logger.info(f"  - {model}")
        if len(all_models) > 20:
            logger.info(f"  ... 还有 {len(all_models) - 20} 个产品型号")
        
        # 检查重复产品型号的冲突情况
        duplicate_models = df[df['产品型号'].duplicated(keep=False)]['产品型号'].unique()
        if len(duplicate_models) > 0:
            logger.info(f"\n存在重复的产品型号 ({len(duplicate_models)} 个):")
            for model in sorted(duplicate_models):
                if len(str(model)) > 0:
                    logger.info(f"  - {model}")
                    
                    # 显示该产品的不同价格
                    model_data = df[df['产品型号'] == model]
                    prices = model_data['单价'].unique()
                    logger.info(f"    价格: {prices}")
                    
                    # 显示哪些购买单位有这个产品
                    units_with_model = model_data['购买单位'].unique()
                    logger.info(f"    购买单位: {units_with_model}")
        
        return units, unit_products, all_models
        
    except Exception as e:
        logger.error(f"分析Sheet1失败: {e}")
        return [], {}, []

def main():
    """主函数"""
    print("=== 分析Sheet1中的购买单位和产品 ===")
    units, unit_products, all_models = analyze_sheet1()
    print(f"\nSheet1中发现:")
    print(f"  - 购买单位: {len(units)} 个")
    print(f"  - 产品型号: {len(all_models)} 个")

if __name__ == "__main__":
    main()
