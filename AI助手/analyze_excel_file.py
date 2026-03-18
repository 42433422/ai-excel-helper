#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析尹玉华132.xlsx文档内容
"""

import pandas as pd
import os

def analyze_excel_file():
    """分析Excel文件内容"""
    
    file_path = "尹玉华132.xlsx"
    
    print("=" * 80)
    print(f"📄 分析文档: {file_path}")
    print("=" * 80)
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return
    
    try:
        # 尝试读取Excel文件
        print("📖 正在读取Excel文件...")
        
        # 获取所有工作表名称
        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
        print(f"📋 工作表数量: {len(sheet_names)}")
        print(f"📋 工作表名称: {sheet_names}")
        
        # 分析每个工作表
        for i, sheet_name in enumerate(sheet_names, 1):
            print(f"\n" + "="*60)
            print(f"📊 工作表 {i}: {sheet_name}")
            print("="*60)
            
            try:
                # 读取工作表
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                print(f"📏 数据维度: {df.shape[0]} 行 × {df.shape[1]} 列")
                print(f"📋 列名: {list(df.columns)}")
                
                # 显示前几行数据
                print(f"\n📋 前5行数据:")
                print(df.head().to_string())
                
                # 检查是否有空值
                null_counts = df.isnull().sum()
                if null_counts.sum() > 0:
                    print(f"\n⚠️  空值统计:")
                    for col, count in null_counts.items():
                        if count > 0:
                            print(f"  {col}: {count} 个空值")
                else:
                    print(f"\n✅ 无空值")
                
                # 数据类型
                print(f"\n📊 数据类型:")
                print(df.dtypes.to_string())
                
            except Exception as e:
                print(f"❌ 读取工作表 {sheet_name} 失败: {e}")
        
        print(f"\n" + "="*60)
        print("✅ 分析完成")
        print("="*60)
        
    except Exception as e:
        print(f"❌ 读取Excel文件失败: {e}")

if __name__ == "__main__":
    analyze_excel_file()