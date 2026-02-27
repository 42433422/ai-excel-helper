#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细检查get_printers()返回的数据格式
"""

import os
import sys
sys.path.append(os.path.dirname(__file__))

from print_utils import get_printers

def check_printer_data():
    """
    检查get_printers()返回的数据格式
    """
    print("=== 检查get_printers()返回数据格式 ===\n")
    
    try:
        printers = get_printers()
        print(f"返回类型: {type(printers)}")
        print(f"数量: {len(printers)}")
        print()
        
        for i, printer in enumerate(printers, 1):
            print(f"打印机 {i}:")
            print(f"  类型: {type(printer)}")
            print(f"  数据: {printer}")
            print(f"  字段:")
            for key, value in printer.items():
                print(f"    {key}: {value}")
            print()
            
        # 检查每个打印机的完整字段
        print("\n=== 检查关键字段 ===")
        for i, printer in enumerate(printers, 1):
            name = printer.get('name', '')
            has_name = 'name' in printer
            print(f"打印机 {i}: {name}")
            print(f"  有name字段: {has_name}")
            print(f"  包含TSC: {'TSC' in name or 'TTP' in name}")
            print()
            
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_printer_data()
