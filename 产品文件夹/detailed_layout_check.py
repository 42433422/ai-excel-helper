#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import os

def check_specific_layouts():
    """检查特定文件的实际列布局"""
    # 重点检查尹玉华1.xlsx（正确）和温总.xlsx（错误）的布局差异
    files_to_check = [
        '发货单/尹玉华1.xlsx',  # 正确示例
        '发货单/温总.xlsx',       # 问题示例
    ]
    
    for file_path in files_to_check:
        print(f"\n=== 详细检查文件: {file_path} ===")
        try:
            # 读取所有工作表
            excel_file = pd.ExcelFile(file_path)
            for sheet_name in excel_file.sheet_names:
                if '出货' in sheet_name or sheet_name in ['出货', '温总', '尹']:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    print(f"\n工作表: {sheet_name}, 形状: {df.shape}")
                    print("列名:")
                    for i, col in enumerate(df.columns):
                        print(f"  {i}: {col}")
                    
                    print("\n前20行详细数据:")
                    for i in range(min(20, len(df))):
                        row_data = []
                        for j in range(min(15, len(df.columns))):
                            value = df.iloc[i, j]
                            if pd.notna(value):
                                value_str = str(value)
                                if len(value_str) > 20:
                                    value_str = value_str[:20] + '...'
                                row_data.append(f'{j}:{value_str}')
                        if row_data:
                            separator = " | "
                            print(f'  行{i+1}: {separator.join(row_data)}')
        except Exception as e:
            print(f"读取文件失败: {e}")
            import traceback
            traceback.print_exc()

def analyze_column_mapping():
    """分析列映射问题"""
    print("\n=== 列映射问题分析 ===")
    print("尹玉华1.xlsx (正确) 的列布局:")
    print("  列0: 日期")
    print("  列2: 产品型号")
    print("  列3: 产品名称")
    print("  列4: 数量/件")
    print("  列5: 规格/KG")
    print("  列6: 数量/KG (公式: =E4*F4)")
    print("  列7: 单价/元")
    print("  列8: 金额/元 (公式: =G4*H4)")
    
    print("\n温总.xlsx (错误) 的实际列布局:")
    print("  列0: 日期")
    print("  列1: 单号")
    print("  列2: 产品型号")
    print("  列3: 产品名称")
    print("  列4: 数量/件")
    print("  列5: 规格/KG")
    print("  列6: 数量/KG (公式: =E4*F4)")
    print("  列7: 单价/元")
    print("  列8: 金额/元 (公式: =G4*H4)")
    
    print("\n问题根源: 自适应列识别逻辑失败，无法正确识别不同文件的列索引！")
    print("解决方案: 重新设计更可靠的列识别逻辑，基于数据特征而非标题！")

if __name__ == "__main__":
    check_specific_layouts()
    analyze_column_mapping()