#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import os

def check_excel_structure():
    """检查Excel文件结构"""
    print("=== 检查Excel文件结构 ===")
    
    # 检查几个其他Excel文件的工作表结构
    files = ['发货单\\侯雪梅.xlsx', '发货单\\刘英.xlsx', '发货单\\志泓.xlsx', '发货单\\现金.xlsx', '发货单\\温总.xlsx']

    for file in files:
        if os.path.exists(file):
            print(f'\n=== {file} ===')
            try:
                excel_file = pd.ExcelFile(file)
                print(f'工作表: {excel_file.sheet_names}')
                
                # 尝试读取第一个工作表
                df = pd.read_excel(file, sheet_name=excel_file.sheet_names[0])
                print(f'形状: {df.shape}')
                print('前2行:')
                for i in range(min(2, len(df))):
                    row_data = []
                    for j in range(min(8, len(df.columns))):
                        value = df.iloc[i, j]
                        if pd.notna(value):
                            row_data.append(f'[{j}:{value}]')
                    if row_data:
                        print(f'  行{i+1}: {" ".join(row_data)}')
                        
            except Exception as e:
                print(f'读取失败: {e}')

if __name__ == "__main__":
    check_excel_structure()