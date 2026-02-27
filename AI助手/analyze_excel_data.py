#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析Excel文件中的产品数据和购买单位信息
"""

import os
import pandas as pd
import json
from datetime import datetime


def analyze_excel_data(excel_file):
    """
    分析Excel文件中的产品数据和购买单位信息
    
    Args:
        excel_file: Excel文件路径
    
    Returns:
        dict: 分析结果
    """
    print(f"=== 分析Excel文件: {excel_file} ===")
    
    try:
        # 读取Excel文件
        xls = pd.ExcelFile(excel_file)
        print(f"Excel文件包含 {len(xls.sheet_names)} 个工作表:")
        for sheet_name in xls.sheet_names:
            print(f"  - {sheet_name}")
        print()
        
        # 分析每个工作表
        analysis_results = {}
        
        for sheet_name in xls.sheet_names:
            print(f"=== 分析工作表: {sheet_name} ===")
            
            # 读取工作表数据
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            
            # 基本信息
            print(f"工作表形状: {df.shape}")
            print(f"列名: {list(df.columns)}")
            print()
            
            # 数据预览
            print("数据预览 (前10行):")
            print(df.head(10))
            print()
            
            # 分析购买单位信息
            unit_columns = []
            for col in df.columns:
                if any(keyword in str(col) for keyword in ['单位', '公司', '客户', '购买', 'buyer', 'company', 'customer']):
                    unit_columns.append(col)
            
            if unit_columns:
                print("找到可能的购买单位列:")
                for col in unit_columns:
                    unique_units = df[col].dropna().unique()
                    print(f"  列 '{col}' 包含 {len(unique_units)} 个唯一值:")
                    for unit in unique_units[:10]:  # 只显示前10个
                        print(f"    - {unit}")
                    if len(unique_units) > 10:
                        print(f"    ... 还有 {len(unique_units) - 10} 个值")
                    print()
            
            # 分析产品相关列
            product_columns = []
            for col in df.columns:
                if any(keyword in str(col) for keyword in ['产品', '型号', '编号', 'product', 'model', 'number', 'code']):
                    product_columns.append(col)
            
            if product_columns:
                print("找到可能的产品相关列:")
                for col in product_columns:
                    unique_values = df[col].dropna().unique()
                    print(f"  列 '{col}' 包含 {len(unique_values)} 个唯一值:")
                    for val in unique_values[:10]:  # 只显示前10个
                        print(f"    - {val}")
                    if len(unique_values) > 10:
                        print(f"    ... 还有 {len(unique_values) - 10} 个值")
                    print()
            
            # 保存分析结果
            analysis_results[sheet_name] = {
                'shape': df.shape,
                'columns': list(df.columns),
                'unit_columns': unit_columns,
                'product_columns': product_columns,
                'sample_data': df.head(5).to_dict('records')
            }
            
    except Exception as e:
        print(f"❌ 分析Excel文件失败: {e}")
        return None
    
    return analysis_results


def main():
    """
    主函数
    """
    # Excel文件路径
    excel_file = "templates/新建 XLSX 工作表 (2).xlsx"
    
    if not os.path.exists(excel_file):
        print(f"❌ Excel文件不存在: {excel_file}")
        return
    
    # 分析Excel文件
    results = analyze_excel_data(excel_file)
    
    if results:
        # 保存分析结果
        output_file = f"excel_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 分析结果已保存到: {output_file}")


if __name__ == "__main__":
    main()
