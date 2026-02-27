#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import os
import re

def extract_customer_info_sheets():
    """提取包含客户信息（购货单位）的表，类似尹工作表格式"""
    print("=" * 80)
    print("=== 提取客户信息表（尹格式） ===")
    print("=" * 80)
    
    # 创建输出目录
    output_dir = "客户信息表"
    if os.path.exists(output_dir):
        for f in os.listdir(output_dir):
            os.remove(os.path.join(output_dir, f))
    else:
        os.makedirs(output_dir)
    
    # 发货单文件列表
    excel_files = [
        ('发货单/尹玉华1.xlsx', '尹'),
        ('发货单/七彩乐园.xlsx', '七彩乐园'),
        ('发货单/侯雪梅.xlsx', '侯雪梅'),
        ('发货单/刘英.xlsx', '刘英'),
        ('发货单/国圣化工.xlsx', '国圣'),
        ('发货单/宗南.xlsx', '宗南'),
        ('发货单/宜榢.xlsx', '宜榢'),
        ('发货单/小洋杨总、.xlsx', '24徐'),
        ('发货单/志泓.xlsx', '志泓'),
        ('发货单/新旺博旺.xlsx', '新旺博旺'),
        ('发货单/温总.xlsx', '温总'),
        ('发货单/澜宇电视柜.xlsx', '澜宇电视柜'),
        ('发货单/现金.xlsx', '现金'),
        ('发货单/迎扬李总(1).xlsx', '迎扬电视墙'),
        ('发货单/迎扬李总.xlsx', '迎扬电视墙'),
        ('发货单/邻居杨总.xlsx', '邻居'),
        ('发货单/邻居贾总.xlsx', '贾总'),
    ]
    
    file_count = 0
    for file_path, sheet_name in excel_files:
        file_name = os.path.basename(file_path).replace('.xlsx', '')
        print(f"\n处理文件: {file_name}")
        
        try:
            # 读取工作表
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            print(f"  工作表: {sheet_name}, 形状: {df.shape}")
            
            # 提取客户名称
            customer_name = ""
            for i in range(min(3, len(df))):
                if len(df.columns) > 0:
                    row_str = str(df.iloc[i, 0]) if i < len(df) else ''
                    if '购货单位' in row_str or '购买单位' in row_str:
                        # 提取客户名称
                        match = re.search(r'[购货购买]单位[（(][^）)]*[）)][：:]\s*(.+?)\s*(?:[\s联系人]|$)', row_str)
                        if match:
                            customer_name = match.group(1).strip()
                        else:
                            parts = row_str.split('：')
                            if len(parts) > 1:
                                customer_name = parts[1].strip().split()[0]
                        break
            
            # 生成输出文件名
            if customer_name:
                safe_name = customer_name.replace('/', '_').replace('\\', '_')
            else:
                safe_name = file_name
            
            output_file = f"{output_dir}/{safe_name}-客户信息.xlsx"
            
            # 保存为Excel文件
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='客户信息', index=False)
            
            print(f"  ✓ 保存: {output_file}")
            print(f"     客户: {customer_name}")
            file_count += 1
            
        except Exception as e:
            print(f"  ✗ 错误: {e}")
    
    print("\n" + "=" * 80)
    print(f"✓ 成功提取 {file_count} 个客户信息表!")
    print(f"  目录: {output_dir}/")
    print("=" * 80)

if __name__ == "__main__":
    extract_customer_info_sheets()