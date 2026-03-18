#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新分析Excel文件结构
"""

import pandas as pd
import os

def reanalyze_excel():
    """重新分析Excel文件结构"""
    
    excel_file = "尹玉华1 - 副本.xlsx"
    
    print("=== 重新分析Excel文件结构 ===")
    
    if not os.path.exists(excel_file):
        print(f"❌ 文件不存在: {excel_file}")
        return None
    
    try:
        # 读取Excel文件
        print(f"📖 读取Excel文件: {excel_file}")
        df = pd.read_excel(excel_file)
        
        print(f"📊 Excel数据形状: {df.shape}")
        print(f"📋 列名: {list(df.columns)}")
        
        # 显示前20行数据
        print("\n📄 前20行数据:")
        print(df.head(20))
        
        # 分析数据模式
        print("\n=== 分析数据模式 ===")
        
        # 统计各列的数据类型和内容
        for i, col in enumerate(df.columns):
            print(f"\n📄 列 {i} ({str(col)}):")
            # 显示该列的前10个非空值
            non_empty_values = df[col].dropna().head(10).tolist()
            print(f"  非空值样本: {non_empty_values}")
            print(f"  非空值数量: {df[col].count()}")
            
            # 检查是否包含"蕊芯"相关数据
            ruixin_count = sum(1 for val in df[col].dropna() if '蕊芯' in str(val))
            if ruixin_count > 0:
                print(f"  包含'蕊芯'的数量: {ruixin_count}")
                print(f"  包含'蕊芯'的样本: {[val for val in df[col].dropna() if '蕊芯' in str(val)][:5]}")
        
        # 查找可能的产品型号列
        print("\n=== 查找产品型号列 ===")
        for i, col in enumerate(df.columns):
            # 检查是否包含产品型号模式（如RX001, 9806A, 6824A等）
            sample_values = df[col].dropna().head(20).tolist()
            model_like_values = []
            for val in sample_values:
                val_str = str(val)
                # 查找可能的型号格式
                if any(pattern in val_str for pattern in ['RX', 'OF-', '9806', '6824', '8520', '9803']):
                    model_like_values.append(val_str)
            
            if model_like_values:
                print(f"\n✅ 列 {i} ({str(col)}) 可能是产品型号列:")
                print(f"  型号样本: {model_like_values}")
        
        return df
        
    except Exception as e:
        print(f"❌ 分析Excel文件失败: {e}")
        return None

def extract_ruixin_prices(df):
    """提取蕊芯价格数据"""
    
    print("\n=== 提取蕊芯价格数据 ===")
    
    # 查找包含"蕊芯"的行
    ruixin_rows = []
    for index, row in df.iterrows():
        for col in df.columns:
            val = str(row[col])
            if '蕊芯' in val:
                ruixin_rows.append((index, row))
                break
    
    print(f"🔍 找到 {len(ruixin_rows)} 行包含'蕊芯'的数据")
    
    # 分析蕊芯数据的结构
    if ruixin_rows:
        print("\n📄 蕊芯数据样本:")
        for i, (index, row) in enumerate(ruixin_rows[:5]):
            print(f"\n  行 {index}:")
            for col in df.columns:
                val = row[col]
                if pd.notna(val):
                    print(f"    {str(col)}: {val}")
    
    return ruixin_rows

def main():
    """主函数"""
    
    df = reanalyze_excel()
    if df is not None:
        extract_ruixin_prices(df)

if __name__ == "__main__":
    main()