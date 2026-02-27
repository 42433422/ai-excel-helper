#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd

def check_file_layout(file_path, file_name):
    """检查文件布局"""
    try:
        excel_file = pd.ExcelFile(file_path)
        print(f'\n=== {file_name} ===')
        print(f'工作表: {excel_file.sheet_names}')
        
        for sheet_name in excel_file.sheet_names:
            if '出货' in sheet_name or sheet_name in ['出货', '出货记录']:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                print(f'工作表: {sheet_name}, 形状: {df.shape}')
                print(f'列数: {len(df.columns)}')
                
                # 显示前10行
                for i in range(min(10, len(df))):
                    row_data = []
                    for j in range(min(15, len(df.columns))):
                        value = df.iloc[i, j]
                        if pd.notna(value):
                            # 截取过长内容
                            value_str = str(value)
                            if len(value_str) > 20:
                                value_str = value_str[:20] + '...'
                            row_data.append(f'{j+1}:{value_str}')
                    if row_data:
                        separator = " | "
                        print(f'  行{i+1}: {separator.join(row_data)}')
                break
    except Exception as e:
        print(f'错误: {e}')

if __name__ == "__main__":
    # 检查问题文件
    check_file_layout('发货单\\刘英.xlsx', '刘英')
    check_file_layout('发货单\\国圣化工.xlsx', '国圣化工')
    check_file_layout('发货单\\侯雪梅.xlsx', '侯雪梅')