#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import os
import re

def extract_customer_sheets():
    """提取包含客户信息（购货单位）的工作表"""
    print("=" * 80)
    print("=== 提取客户信息表（购货单位） ===")
    print("=" * 80)
    
    # 创建输出目录
    output_dir = "客户信息表"
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
    
    # 客户信息表工作表名称（与文件名相关或包含客户信息）
    customer_sheet_mapping = {
        '尹玉华1.xlsx': '尹',
        '七彩乐园.xlsx': '七彩乐园',
        '侯雪梅.xlsx': '侯雪梅',
        '刘英.xlsx': '刘英',
        '国圣化工.xlsx': '国圣',
        '宗南.xlsx': '宗南',
        '宜榢.xlsx': '宜榢',
        '小洋杨总、.xlsx': '24徐',  # 可能需要调整
        '志泓.xlsx': '志泓',
        '新旺博旺.xlsx': '新旺博旺',
        '温总.xlsx': '温总',
        '澜宇电视柜.xlsx': '澜宇电视柜',
        '现金.xlsx': '现金',
        '迎扬李总(1).xlsx': '迎扬电视墙',
        '迎扬李总.xlsx': '迎扬电视墙',
        '邻居杨总.xlsx': '邻居',
        '邻居贾总.xlsx': '贾总',
    }
    
    file_count = 0
    for file_path in excel_files:
        file_name = os.path.basename(file_path)
        print(f"\n处理文件: {file_name}")
        
        try:
            excel_file = pd.ExcelFile(file_path)
            sheets = excel_file.sheet_names
            print(f"  工作表: {sheets}")
            
            # 优先使用映射的工作表
            sheet_name = customer_sheet_mapping.get(file_name)
            if sheet_name and sheet_name in sheets:
                print(f"  使用映射: {sheet_name}")
            else:
                # 查找包含客户信息的工作表
                sheet_name = None
                for s in sheets:
                    # 检查第一行是否包含'购货单位'
                    try:
                        df = pd.read_excel(file_path, sheet_name=s, nrows=5)
                        for i in range(min(5, len(df))):
                            if len(df.columns) > 0:
                                row_str = str(df.iloc[i, 0]) if i < len(df) else ''
                                if '购货单位' in row_str or '购买单位' in row_str:
                                    sheet_name = s
                                    print(f"  找到客户信息表: {s}")
                                    break
                        if sheet_name:
                            break
                    except:
                        continue
                
                # 如果没找到，使用文件名对应的工作表或第一个
                if not sheet_name:
                    # 尝试找与文件名匹配的工作表
                    base_name = file_name.replace('.xlsx', '')
                    for s in sheets:
                        if base_name in s or s in base_name:
                            sheet_name = s
                            print(f"  使用文件名匹配: {s}")
                            break
                    
                    # 如果还是没有，使用第一个工作表
                    if not sheet_name:
                        sheet_name = sheets[0]
                        print(f"  使用第一个工作表: {sheets[0]}")
            
            # 读取工作表数据
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            print(f"  数据形状: {df.shape}")
            
            # 提取客户名称
            customer_name = ""
            for i in range(min(5, len(df))):
                if len(df.columns) > 0:
                    row_str = str(df.iloc[i, 0]) if i < len(df) else ''
                    if '购货单位' in row_str or '购买单位' in row_str:
                        # 提取客户名称
                        match = re.search(r'[购货购买]单位[（(][^）)]*[）)][：:]\s*(.+?)\s*(?:[\s联系人]|$)', row_str)
                        if match:
                            customer_name = match.group(1).strip()
                        else:
                            # 简单提取冒号后面的内容
                            parts = row_str.split('：')
                            if len(parts) > 1:
                                customer_name = parts[1].strip().split()[0]
                        break
            
            # 生成输出文件名
            if customer_name:
                safe_name = customer_name.replace('/', '_').replace('\\', '_')
            else:
                safe_name = file_name.replace('.xlsx', '')
            
            output_file = f"{output_dir}/{safe_name}-客户信息.xlsx"
            
            # 保存为Excel文件
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='客户信息', index=False)
            
            print(f"  ✓ 保存: {output_file} (客户: {customer_name})")
            file_count += 1
            
        except Exception as e:
            print(f"  ✗ 错误: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print(f"✓ 成功提取 {file_count} 个客户信息表!")
    print(f"  目录: {output_dir}/")
    print("=" * 80)

if __name__ == "__main__":
    extract_customer_sheets()