#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import os

def debug_ruixin1_data():
    """详细调试蕊芯家私1的数据提取"""
    
    excel_path = '../出货记录/蕊芯家私1/蕊芯家私1出货记录.xlsx'
    
    try:
        print(f'📋 调试Excel数据提取: {excel_path}')
        
        # 读取Excel文件
        all_sheets = pd.read_excel(excel_path, sheet_name=None)
        df = all_sheets['25出货']
        
        print(f'\n📄 原始数据:')
        for index, row in df.iterrows():
            print(f'  行 {index}:')
            for i, col_name in enumerate(df.columns):
                print(f'    {col_name}: {row.iloc[i]}')
            print()
        
        # 模拟我们的提取逻辑
        print(f'\n🔍 模拟提取逻辑:')
        for index, row in df.iterrows():
            # 跳过空行和标题行
            if pd.isna(row.iloc[0]) or str(row.iloc[0]).strip() == '':
                continue
            first_cell = str(row.iloc[0]).strip()
            if any(keyword in first_cell for keyword in ['日期', '单号', '产品', '合计', '总计']):
                continue
            
            print(f'  处理行 {index}: {first_cell}')
            
            # 提取订单号
            order_number = ""
            if len(row) > 1 and pd.notna(row.iloc[1]):
                order_value = str(row.iloc[1]).strip()
                if order_value and order_value != '单号':
                    import re
                    order_match = re.search(r'[A-Z0-9\-_]+', order_value)
                    if order_match:
                        order_number = order_match.group()
                    else:
                        order_number = f"ORDER_{index}"
            
            print(f'    订单号: {order_number}')
            
            # 提取产品名称
            product_name = ""
            if len(row) > 5 and pd.notna(row.iloc[5]):
                product_name = str(row.iloc[5]).strip()
            print(f'    产品名称: {product_name}')
            
            # 提取金额
            amount = 0.0
            
            # 先检查第10列（金额/元）
            if len(row) > 10 and pd.notna(row.iloc[10]):
                try:
                    amount = float(row.iloc[10])
                    print(f'    第10列金额: {amount}')
                except:
                    pass
            
            # 如果没有找到金额，尝试从其他列查找
            if amount == 0.0:
                for i, value in enumerate(row):
                    if pd.notna(value):
                        try:
                            amount = float(value)
                            if amount > 0 and amount < 1000000:
                                print(f'    第{i}列金额: {amount}')
                                break
                        except:
                            continue
            
            print(f'    最终金额: {amount}')
            print()
    
    except Exception as e:
        print(f'❌ 调试失败: {e}')

if __name__ == '__main__':
    debug_ruixin1_data()