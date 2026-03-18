#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd

# 读取尹工作表
df = pd.read_excel('发货单/尹玉华1.xlsx', sheet_name='尹')

print('=== 尹工作表结构 ===')
print(f'形状: {df.shape}')
print(f'列数: {len(df.columns)}')
print(f'列名: {list(df.columns)}')

print('\n前5行数据:')
for i in range(min(5, len(df))):
    row_data = []
    for j in range(len(df.columns)):
        value = df.iloc[i, j]
        if pd.notna(value):
            row_data.append(f'{j+1}:{value}')
    if row_data:
        print(f'行{i+1}: {" | ".join(row_data)}')

print('\n' + '='*50)
print('数据类型:')
print(df.dtypes)