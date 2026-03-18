#!/usr/bin/env python3
# 检查新的蕊芯家私1数据

import pandas as pd
import os

def check_new_ruixin_data():
    """检查新的蕊芯家私1数据"""
    print("=== 检查新的蕊芯家私1数据 ===")
    
    # 读取新的Excel文件
    file_path = "c:\\Users\\97088\\Desktop\\新建文件夹 (4)\\AI助手\\templates\\新建 XLSX 工作表 (2).xlsx"
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return
    
    try:
        # 读取所有sheet
        excel_file = pd.ExcelFile(file_path)
        print(f"Sheet列表: {excel_file.sheet_names}")
        
        # 检查所有Sheet
        for sheet_name in excel_file.sheet_names:
            print(f"\n=== 检查 {sheet_name} ===")
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            print(f"{sheet_name}数据形状: {df.shape}")
            print(f"列名: {list(df.columns)}")
            
            if not df.empty:
                print(f"前10行数据:")
                print(df.head(10))
                
                # 检查是否有数据
                non_empty_rows = df.dropna(how='all')
                print(f"非空行数: {len(non_empty_rows)}")
            else:
                print(f"{sheet_name}是空的")
        
    except Exception as e:
        print(f"❌ 读取Excel文件失败: {e}")

if __name__ == "__main__":
    check_new_ruixin_data()