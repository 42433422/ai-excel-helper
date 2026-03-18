#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import os

def copy_sheets_directly():
    """直接复制工作表保存"""
    print("=== 直接复制工作表 ===\n")
    
    # 工作表映射：文件 -> 工作表名
    mapping = {
        '发货单/尹玉华1.xlsx': '尹',
        '发货单/七彩乐园.xlsx': '七彩乐园',
        '发货单/侯雪梅.xlsx': '侯雪梅',
        '发货单/刘英.xlsx': '刘英',
        '发货单/国圣化工.xlsx': '国圣',
        '发货单/宗南.xlsx': '宗南',
        '发货单/宜榢.xlsx': '宜榢',
        '发货单/小洋杨总、.xlsx': '24徐',
        '发货单/志泓.xlsx': '志泓',
        '发货单/新旺博旺.xlsx': '新旺博旺',
        '发货单/温总.xlsx': '温总',
        '发货单/澜宇电视柜.xlsx': '澜宇电视柜',
        '发货单/现金.xlsx': '现金',
        '发货单/迎扬李总(1).xlsx': '迎扬电视墙',
        '发货单/迎扬李总.xlsx': '迎扬电视墙',
        '发货单/邻居杨总.xlsx': '邻居',
        '发货单/邻居贾总.xlsx': '贾总',
    }
    
    count = 0
    for file_path, sheet_name in mapping.items():
        file_name = os.path.basename(file_path)
        print(f"复制: {file_name} -> {sheet_name}.xlsx")
        
        try:
            # 读取工作表
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            # 直接保存，不做任何处理
            output_file = f"{sheet_name}.xlsx"
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            print(f"  ✓ 完成")
            count += 1
        except Exception as e:
            print(f"  ✗ 错误: {e}")
    
    print(f"\n完成！共 {count} 个文件")

if __name__ == "__main__":
    copy_sheets_directly()