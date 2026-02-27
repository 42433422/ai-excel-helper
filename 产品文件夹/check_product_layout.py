#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd

def check_product_layout():
    """检查产品信息的列布局"""
    print("=== 检查产品信息列布局 ===")
    
    # 检查几个有问题的文件
    files = [
        '发货单\\刘英.xlsx',
        '发货单\\志泓.xlsx', 
        '发货单\\温总.xlsx',
        '发货单\\邻居杨总.xlsx'
    ]

    for file in files:
        print(f'\n=== {file} ===')
        try:
            # 尝试读取出货工作表
            df = pd.read_excel(file, sheet_name='出货')
            print(f'形状: {df.shape}')
            print(f'列数: {len(df.columns)}')
            print('前3行数据:')
            for i in range(min(3, len(df))):
                row_data = []
                for j in range(min(15, len(df.columns))):
                    value = df.iloc[i, j]
                    if pd.notna(value):
                        row_data.append(f'{j+1}:{value}')
                if row_data:
                    print(f'  行{i+1}: {" ".join(row_data)}')
                    
        except Exception as e:
            print(f'读取失败: {e}')

if __name__ == "__main__":
    check_product_layout()