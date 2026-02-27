#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查Excel文件中的规格信息
"""

import pandas as pd

excel_path = "尹玉华1 - 副本.xlsx"

print("=== 检查Excel文件中的规格信息 ===")

# 读取Sheet2工作表
df = pd.read_excel(excel_path, sheet_name='Sheet2', header=None)
df.columns = ['产品编号', '产品名称', '规格', '内部价格', '空列', '外部价格']

# 从第3行开始（跳过表头行和标题行）
product_data = df.iloc[2:].copy()

print("所有产品的规格信息:")
for idx, row in product_data.iterrows():
    code = str(row['产品编号']).strip()
    name = str(row['产品名称']).strip()
    spec = str(row['规格']).strip()
    
    # 跳过空值和无效行
    if code in ['nan', '', 'None'] or name in ['nan', '', 'None']:
        continue
    
    # 跳过表头行
    if code == '产品编号' or name == '产品名称':
        continue
    
    print(f"  {code}: {name} - 规格: '{spec}'")

print("\n=== 检查完成 ===")
