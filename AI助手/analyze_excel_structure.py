#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析Excel文件结构和数据格式
"""

import pandas as pd
import numpy as np
import os
import re
from datetime import datetime

class ExcelAnalyzer:
    """Excel文件分析器"""
    
    def __init__(self, file_path):
        self.file_path = file_path
        self.worksheets = {}
        self.analysis_results = {}
    
    def analyze(self):
        """分析Excel文件"""
        try:
            # 读取Excel文件
            xls = pd.ExcelFile(self.file_path)
            
            print(f"=== Excel文件分析报告 ===")
            print(f"文件路径: {self.file_path}")
            print(f"文件大小: {os.path.getsize(self.file_path) / 1024:.2f} KB")
            print(f"工作表数量: {len(xls.sheet_names)}")
            print(f"工作表名称: {xls.sheet_names}")
            print()
            
            # 分析每个工作表
            for sheet_name in xls.sheet_names:
                print(f"=== 工作表: {sheet_name} ===")
                
                # 读取工作表
                df = pd.read_excel(xls, sheet_name)
                
                print(f"行数: {len(df)}")
                print(f"列数: {len(df.columns)}")
                print(f"列名: {list(df.columns)}")
                print()
                
                # 分析数据类型和格式
                print("列类型分析:")
                for col in df.columns:
                    non_null_count = df[col].count()
                    null_count = df[col].isnull().sum()
                    dtype = str(df[col].dtype)
                    
                    # 分析数据格式
                    sample_values = df[col].dropna().head(10)
                    sample_str = ', '.join([str(val) for val in sample_values])
                    
                    # 检查是否为日期格式
                    is_date = self._is_date_column(df[col])
                    
                    # 检查是否为型号格式
                    has_model_pattern = self._has_model_pattern(sample_values)
                    
                    print(f"  {col}:")
                    print(f"    非空值: {non_null_count}")
                    print(f"    空值: {null_count}")
                    print(f"    类型: {dtype}")
                    print(f"    是否日期: {is_date}")
                    print(f"    包含型号格式: {has_model_pattern}")
                    print(f"    示例值: {sample_str[:100]}...")
                    print()
                
                # 分析日期格式型号
                self._analyze_date_models(df)
                
                # 分析公司/购买单位数据
                self._analyze_purchase_units(df)
                
                print()
                
        except Exception as e:
            print(f"分析失败: {e}")
    
    def _is_date_column(self, series):
        """检查列是否为日期格式"""
        try:
            pd.to_datetime(series, errors='coerce').notnull().sum() > 0
            return True
        except:
            return False
    
    def _has_model_pattern(self, sample_values):
        """检查是否包含型号格式"""
        model_patterns = [
            r'^[A-Za-z0-9]+$',  # 纯字母数字
            r'^\d{4}[A-Za-z]$',  # 日期格式如0514a
            r'^[A-Za-z]+\d+$',   # 字母开头数字结尾
            r'^\d+[A-Za-z]+$'    # 数字开头字母结尾
        ]
        
        for val in sample_values:
            val_str = str(val)
            for pattern in model_patterns:
                if re.match(pattern, val_str):
                    return True
        return False
    
    def _analyze_date_models(self, df):
        """分析日期格式型号"""
        print("日期格式型号分析:")
        date_model_pattern = r'^(\d{4})([A-Za-z])$'  # 如0514a
        
        for col in df.columns:
            if df[col].dtype == 'object':
                date_models = []
                for val in df[col].dropna():
                    val_str = str(val)
                    match = re.match(date_model_pattern, val_str)
                    if match:
                        date_part = match.group(1)
                        letter_part = match.group(2)
                        date_models.append((val_str, date_part, letter_part))
                
                if date_models:
                    print(f"  列 '{col}' 中发现 {len(date_models)} 个日期格式型号:")
                    for model, date_part, letter_part in date_models[:5]:
                        print(f"    {model} -> 日期: {date_part[:2]}月{date_part[2:]}日, 序号: {letter_part}")
                    if len(date_models) > 5:
                        print(f"    ... 还有 {len(date_models) - 5} 个更多")
                    print()
    
    def _analyze_purchase_units(self, df):
        """分析购买单位数据"""
        print("购买单位分析:")
        
        # 尝试识别购买单位列
        unit_columns = []
        unit_keywords = ['公司', '客户', '单位', '购买单位', '客户单位', '购货单位']
        
        for col in df.columns:
            col_lower = str(col).lower()
            for keyword in unit_keywords:
                if keyword in str(col):
                    unit_columns.append(col)
                    break
        
        if unit_columns:
            print(f"  可能的购买单位列: {unit_columns}")
            
            for col in unit_columns:
                unique_units = df[col].dropna().unique()
                print(f"  列 '{col}' 中的购买单位 ({len(unique_units)} 个):")
                for unit in unique_units[:10]:
                    print(f"    {unit}")
                if len(unique_units) > 10:
                    print(f"    ... 还有 {len(unique_units) - 10} 个更多")
                print()
        else:
            print("  未识别到购买单位列")
        
    def _detect_model_number_pattern(self, df):
        """检测型号编号模式"""
        print("型号编号模式检测:")
        
        for col in df.columns:
            if df[col].dtype == 'object':
                # 检测不同模式的型号
                patterns = {
                    '纯数字': r'^\d+$',
                    '纯字母': r'^[A-Za-z]+$',
                    '字母数字组合': r'^[A-Za-z0-9]+$',
                    '日期格式': r'^\d{4}[A-Za-z]$',
                    '带分隔符': r'^[A-Za-z0-9]+[-_][A-Za-z0-9]+$'
                }
                
                pattern_counts = {}
                for pattern_name, pattern in patterns.items():
                    count = 0
                    for val in df[col].dropna():
                        if re.match(pattern, str(val)):
                            count += 1
                    pattern_counts[pattern_name] = count
                
                total_values = df[col].count()
                if total_values > 0:
                    print(f"  列 '{col}' 型号模式:")
                    for pattern_name, count in pattern_counts.items():
                        if count > 0:
                            percentage = (count / total_values) * 100
                            print(f"    {pattern_name}: {count} ({percentage:.1f}%)")
                    print()

if __name__ == "__main__":
    # Excel文件路径
    excel_file = "新建 XLSX 工作表 (2).xlsx"
    
    if os.path.exists(excel_file):
        analyzer = ExcelAnalyzer(excel_file)
        analyzer.analyze()
    else:
        print(f"文件不存在: {excel_file}")
        # 尝试其他可能的路径
        alt_path = os.path.join(os.getcwd(), excel_file)
        if os.path.exists(alt_path):
            analyzer = ExcelAnalyzer(alt_path)
            analyzer.analyze()
        else:
            print(f"备用路径也不存在: {alt_path}")
