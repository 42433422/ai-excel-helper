#!/usr/bin/env python3
# 读取内部价Excel文件并分析内容

import pandas as pd
import os

def read_internal_prices():
    """读取内部价Excel文件"""
    print("=== 读取内部价Excel文件 ===")
    
    file_path = "c:\\Users\\97088\\Desktop\\新建文件夹 (4)\\AI助手\\templates\\尹玉华1 - 副本.xlsx"
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return
    
    try:
        # 读取Excel文件的所有工作表
        excel_file = pd.ExcelFile(file_path)
        print(f"Excel文件工作表: {excel_file.sheet_names}")
        print()
        
        # 读取每个工作表
        for sheet_name in excel_file.sheet_names:
            print(f"--- 工作表: {sheet_name} ---")
            
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                print(f"数据形状: {df.shape}")
                print(f"列名: {list(df.columns)}")
                print()
                
                # 显示前几行数据
                print("前5行数据:")
                print(df.head())
                print()
                
                # 查找包含价格相关的列
                price_columns = []
                for col in df.columns:
                    if any(keyword in str(col).lower() for keyword in ['价', 'price', '单价', '金额', '钱']):
                        price_columns.append(col)
                
                if price_columns:
                    print(f"价格相关列: {price_columns}")
                    for col in price_columns:
                        print(f"  {col}: {df[col].dropna().tolist()[:10]}")  # 显示前10个非空值
                    print()
                
            except Exception as e:
                print(f"❌ 读取工作表 {sheet_name} 失败: {e}")
            
            print("=" * 50)
            print()
        
    except Exception as e:
        print(f"❌ 读取Excel文件失败: {e}")

if __name__ == "__main__":
    read_internal_prices()