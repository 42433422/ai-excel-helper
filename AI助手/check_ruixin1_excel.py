#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import os

def check_ruixin1_excel():
    """检查蕊芯家私1的Excel文件实际内容"""
    
    excel_path = '../出货记录/蕊芯家私1/蕊芯家私1出货记录.xlsx'
    
    if not os.path.exists(excel_path):
        print(f'❌ 文件不存在: {excel_path}')
        return
    
    try:
        print(f'📋 检查Excel文件: {excel_path}')
        
        # 读取所有工作表
        all_sheets = pd.read_excel(excel_path, sheet_name=None)
        print(f'📊 工作表: {list(all_sheets.keys())}')
        
        # 检查25出货工作表
        if '25出货' in all_sheets:
            df = all_sheets['25出货']
            print(f'\n📄 25出货工作表:')
            print(f'  - 行数: {len(df)}')
            print(f'  - 列数: {len(df.columns)}')
            print(f'  - 列名: {list(df.columns)}')
            
            if len(df) > 0:
                print(f'  - 前5行数据:')
                print(df.head().to_string())
                
                # 检查是否有有效数据行
                valid_rows = 0
                for index, row in df.iterrows():
                    # 跳过空行和标题行
                    if pd.isna(row.iloc[0]) or str(row.iloc[0]).strip() == '':
                        continue
                    first_cell = str(row.iloc[0]).strip()
                    if any(keyword in first_cell for keyword in ['日期', '单号', '产品', '合计', '总计']):
                        continue
                    valid_rows += 1
                
                print(f'  - 有效数据行数: {valid_rows}')
            else:
                print(f'  - 工作表为空')
        else:
            print('❌ 未找到25出货工作表')
            
        # 检查其他工作表
        for sheet_name, df in all_sheets.items():
            if sheet_name != '25出货':
                print(f'\n📄 {sheet_name}工作表:')
                print(f'  - 行数: {len(df)}')
                if len(df) > 0:
                    print(f'  - 前3行:')
                    print(df.head(3).to_string())
    
    except Exception as e:
        print(f'❌ 读取Excel文件失败: {e}')

if __name__ == '__main__':
    check_ruixin1_excel()