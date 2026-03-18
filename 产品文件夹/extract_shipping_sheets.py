#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import os

def extract_shipping_sheets():
    """提取每个Excel文件中的出货/送货数据工作表"""
    print("=" * 80)
    print("=== 提取送货单数据 ===")
    print("=" * 80)
    
    # 创建输出目录
    output_dir = "送货单数据"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 发货单文件列表
    excel_files = [
        '发货单/尹玉华1.xlsx',
        '发货单/七彩乐园.xlsx',
        '发货单/侯雪梅.xlsx',
        '发货单/刘英.xlsx',
        '发货单/国圣化工.xlsx',
        '发货单/宗南.xlsx',
        '发货单/宜榢.xlsx',
        '发货单/小洋杨总、.xlsx',
        '发货单/志泓.xlsx',
        '发货单/新旺博旺.xlsx',
        '发货单/温总.xlsx',
        '发货单/澜宇电视柜.xlsx',
        '发货单/现金.xlsx',
        '发货单/迎扬李总(1).xlsx',
        '发货单/迎扬李总.xlsx',
        '发货单/邻居杨总.xlsx',
        '发货单/邻居贾总.xlsx',
    ]
    
    # 优先选择的工作表名称（按优先级排序）
    priority_sheets = ['出货', '25出货', '现金', '25年出货']
    
    file_count = 0
    for file_path in excel_files:
        file_name = os.path.basename(file_path).replace('.xlsx', '')
        print(f"\n处理文件: {file_name}")
        
        try:
            excel_file = pd.ExcelFile(file_path)
            sheets = excel_file.sheet_names
            print(f"  工作表: {sheets}")
            
            # 查找优先的出货工作表
            selected_sheet = None
            for priority in priority_sheets:
                if priority in sheets:
                    selected_sheet = priority
                    break
            
            # 如果没有找到优先的，选择第一个包含"出货"或"现金"的工作表
            if not selected_sheet:
                for sheet in sheets:
                    if '出货' in sheet or '现金' in sheet:
                        selected_sheet = sheet
                        break
            
            # 如果还是没有，选择第一个工作表
            if not selected_sheet:
                selected_sheet = sheets[0]
            
            print(f"  选择工作表: {selected_sheet}")
            
            # 读取工作表数据
            df = pd.read_excel(file_path, sheet_name=selected_sheet)
            print(f"  数据形状: {df.shape}")
            
            # 保存为单独的Excel文件
            output_file = f"{output_dir}/{file_name}-送货单.xlsx"
            
            # 创建新的Excel写入器
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='送货单', index=False)
            
            print(f"  ✓ 保存: {output_file}")
            file_count += 1
            
        except Exception as e:
            print(f"  ✗ 错误: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print(f"✓ 成功提取 {file_count} 个送货单数据文件!")
    print(f"  目录: {output_dir}/")
    print("=" * 80)

if __name__ == "__main__":
    extract_shipping_sheets()