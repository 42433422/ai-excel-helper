#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专门分析尹玉华132.xlsx中的"25年出货"工作表布局
"""

import pandas as pd
import numpy as np

def analyze_25_shipment_layout():
    """详细分析25年出货工作表的布局"""
    
    file_path = "尹玉华132.xlsx"
    
    print("=" * 80)
    print("📄 专门分析: 尹玉华132.xlsx - 25年出货工作表布局")
    print("=" * 80)
    
    try:
        # 读取"25年出货"工作表
        print("📖 正在读取25年出货工作表...")
        df = pd.read_excel(file_path, sheet_name="25年出货")
        
        print(f"📏 数据维度: {df.shape[0]} 行 × {df.shape[1]} 列")
        print(f"📋 原始列名: {list(df.columns)}")
        
        # 分析数据布局
        print(f"\n" + "="*60)
        print("🔍 数据布局分析")
        print("="*60)
        
        # 显示前15行数据以了解结构
        print(f"\n📋 前15行数据（了解布局结构）:")
        for i in range(min(15, len(df))):
            print(f"\n第{i+1}行:")
            row_data = []
            for j, col in enumerate(df.columns):
                value = df.iloc[i, j]
                if pd.notna(value):
                    row_data.append(f"列{j+1}({col}): {value}")
                else:
                    row_data.append(f"列{j+1}({col}): [空]")
            print("  " + " | ".join(row_data[:10]))  # 只显示前10列
        
        # 分析表头结构
        print(f"\n" + "="*60)
        print("🏗️ 表头结构分析")
        print("="*60)
        
        # 检查前几行是否包含表头信息
        header_candidates = []
        for i in range(min(5, len(df))):
            row = df.iloc[i]
            non_null_count = row.notna().sum()
            if non_null_count > 3:  # 如果这一行有超过3个非空值，可能是表头
                header_candidates.append((i, non_null_count, list(row.dropna().values)))
        
        print(f"🔍 可能的表头行:")
        for i, count, values in header_candidates:
            print(f"  第{i+1}行 ({count}个非空值): {values}")
        
        # 分析客户数据分布
        print(f"\n" + "="*60)
        print("👥 客户数据分布分析")
        print("="*60)
        
        # 查找客户列（通常在第一列或前面几列）
        customer_column = None
        for col_idx in range(min(5, len(df.columns))):
            col = df.columns[col_idx]
            unique_values = df.iloc[:, col_idx].dropna().unique()
            # 检查是否包含常见的客户名
            customer_names = ['蕊芯', '杜克旗', '七彩', '尹玉华']
            if any(name in str(unique_values).lower() for name in customer_names):
                customer_column = col_idx
                break
        
        if customer_column is not None:
            print(f"🎯 客户列识别: 第{customer_column+1}列 ({df.columns[customer_column]})")
            customers = df.iloc[:, customer_column].dropna().value_counts()
            print(f"📊 客户分布:")
            for customer, count in customers.head(10).items():
                print(f"  {customer}: {count}条记录")
        
        # 分析数值列（可能是数量、价格等）
        print(f"\n" + "="*60)
        print("📊 数值列分析")
        print("="*60)
        
        numeric_columns = []
        for i, col in enumerate(df.columns):
            numeric_data = pd.to_numeric(df.iloc[:, i], errors='coerce')
            non_null_count = numeric_data.notna().sum()
            if non_null_count > 10:  # 如果有超过10个数值
                numeric_columns.append((i, col, non_null_count))
                print(f"第{i+1}列 ({col}): {non_null_count}个数值")
                # 显示数值列的统计信息
                numeric_data_clean = numeric_data.dropna()
                if len(numeric_data_clean) > 0:
                    print(f"  数值范围: {numeric_data_clean.min():.2f} ~ {numeric_data_clean.max():.2f}")
                    print(f"  平均值: {numeric_data_clean.mean():.2f}")
        
        # 查找典型的出货数据行
        print(f"\n" + "="*60)
        print("📦 典型出货数据行分析")
        print("="*60)
        
        # 查找包含产品信息的行
        product_keywords = ['PE', 'PU', 'NC', '白底漆', '稀释剂', '哑光', '清面漆']
        product_rows = []
        
        for i in range(len(df)):
            row_str = ' '.join([str(val) for val in df.iloc[i].values if pd.notna(val)])
            if any(keyword in row_str for keyword in product_keywords):
                product_rows.append((i, row_str[:100]))  # 只显示前100个字符
        
        print(f"🔍 找到 {len(product_rows)} 行包含产品信息:")
        for i, (row_idx, content) in enumerate(product_rows[:10]):  # 只显示前10行
            print(f"第{row_idx+1}行: {content}")
        
        # 尝试重新构建标准化的表格结构
        print(f"\n" + "="*60)
        print("🔄 推测的标准表格结构")
        print("="*60)
        
        # 基于分析结果推测列含义
        column_meanings = {}
        for i, col in enumerate(df.columns):
            if i == customer_column:
                column_meanings[col] = "客户名称"
            elif i in [item[0] for item in numeric_columns[:5]]:
                # 检查数值列的特征
                numeric_data = pd.to_numeric(df.iloc[:, i], errors='coerce').dropna()
                if len(numeric_data) > 0:
                    mean_val = numeric_data.mean()
                    if 10 <= mean_val <= 100:  # 可能是单价
                        column_meanings[col] = "单价"
                    elif 100 <= mean_val <= 10000:  # 可能是金额
                        column_meanings[col] = "金额"
                    elif 1 <= mean_val <= 500:  # 可能是数量
                        column_meanings[col] = "数量"
                    else:
                        column_meanings[col] = "其他数值"
                else:
                    column_meanings[col] = "文字信息"
            else:
                column_meanings[col] = "其他信息"
        
        print("🎯 推测的列含义:")
        for col, meaning in column_meanings.items():
            print(f"  {col} → {meaning}")
        
        print(f"\n" + "="*60)
        print("✅ 25年出货工作表布局分析完成")
        print("="*60)
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")

if __name__ == "__main__":
    analyze_25_shipment_layout()