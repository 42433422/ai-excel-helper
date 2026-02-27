#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd

# 检查提取的客户信息表
df = pd.read_excel('客户信息表/蕊芯-客户信息.xlsx', sheet_name='客户信息')

print('=== 蕊芯-客户信息表 ===')
print(f'形状: {df.shape}')
print(f'列数: {len(df.columns)}')

print('\n前5行数据:')
for i in range(min(5, len(df))):
    row_data = []
    for j in range(min(10, len(df.columns))):
        value = df.iloc[i, j]
        if pd.notna(value):
            value_str = str(value)
            if len(value_str) > 25:
                value_str = value_str[:25] + '...'
            row_data.append(f'{j+1}:{value_str}')
    if row_data:
        print(f'行{i+1}: {" | ".join(row_data)}')