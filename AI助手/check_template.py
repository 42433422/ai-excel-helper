#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pandas as pd

def check_template():
    # 检查模板文件
    template_path = '../出货记录/出货记录模板.xlsx'
    print('📋 检查模板文件:', template_path)
    
    if os.path.exists(template_path):
        try:
            df = pd.read_excel(template_path, sheet_name=None)
            print('✅ 模板文件存在')
            print(f'📊 工作表: {list(df.keys())}')
            
            for sheet_name, data in df.items():
                print(f'\n📄 工作表 "{sheet_name}": {data.shape[0]} 行, {data.shape[1]} 列')
                if not data.empty:
                    print(f'   列名: {list(data.columns)}')
                    print(f'   前3行数据:')
                    print(data.head(3).to_string())
        except Exception as e:
            print(f'❌ 读取模板文件失败: {e}')
    else:
        print('❌ 模板文件不存在')
        
    # 检查蕊芯家私1的Excel文件
    ruixin_path = '../出货记录/蕊芯家私1/蕊芯家私1出货记录.xlsx'
    print(f'\n📋 检查蕊芯家私1文件: {ruixin_path}')
    
    if os.path.exists(ruixin_path):
        try:
            df = pd.read_excel(ruixin_path, sheet_name=None)
            print('✅ 蕊芯家私1文件存在')
            print(f'📊 工作表: {list(df.keys())}')
            
            for sheet_name, data in df.items():
                print(f'\n📄 工作表 "{sheet_name}": {data.shape[0]} 行, {data.shape[1]} 列')
                if not data.empty and sheet_name == '25出货':
                    print(f'   列名: {list(data.columns)}')
                    print(f'   数据内容:')
                    print(data.to_string())
        except Exception as e:
            print(f'❌ 读取蕊芯家私1文件失败: {e}')
    else:
        print('❌ 蕊芯家私1文件不存在')

if __name__ == '__main__':
    check_template()