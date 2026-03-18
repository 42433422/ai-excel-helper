#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细追踪标签打印的完整过程
"""

import os
import sys
sys.path.append(os.path.dirname(__file__))

from print_utils import get_printers, print_document

def debug_label_print():
    """
    详细追踪标签打印过程
    """
    print("=== 详细追踪标签打印过程 ===\n")
    
    # 步骤1: 获取打印机列表
    print("步骤1: 获取打印机列表")
    printers = get_printers()
    print(f"  找到 {len(printers)} 个打印机:")
    for i, p in enumerate(printers, 1):
        name = p.get('name', '')
        is_default = p.get('is_default', False)
        print(f"    {i}. {name} (默认: {is_default})")
    print()
    
    # 步骤2: 查找TSC打印机
    print("步骤2: 查找TSC TTP-244打印机")
    label_printer = None
    for printer in printers:
        name = printer.get('name', '')
        if 'TSC TTP-244' in name or 'TTP-244' in name:
            label_printer = printer
            print(f"  ✅ 找到标签打印机: {name}")
            break
    
    if not label_printer:
        print("  ❌ 未找到TSC打印机")
        return
    print()
    
    # 步骤3: 检查label_printer数据
    print("步骤3: 检查label_printer数据")
    print(f"  label_printer: {label_printer}")
    printer_name = label_printer.get('name', '')
    print(f"  printer_name: {printer_name}")
    print()
    
    # 步骤4: 调用print_document
    print("步骤4: 调用print_document()")
    pdf_path = "商标标签完整版.pdf"
    if not os.path.exists(pdf_path):
        print(f"  ❌ PDF文件不存在: {pdf_path}")
        return
    
    print(f"  pdf_path: {pdf_path}")
    print(f"  printer_name: {printer_name}")
    print()
    
    # 步骤5: 执行打印
    print("步骤5: 执行打印")
    print(f"  调用 print_document('{pdf_path}', '{printer_name}')")
    result = print_document(pdf_path, printer_name)
    print()
    
    # 步骤6: 检查结果
    print("步骤6: 检查打印结果")
    print(f"  success: {result.get('success')}")
    print(f"  message: {result.get('message')}")
    print(f"  printer: {result.get('printer')}")
    print()
    
    # 步骤7: 验证打印机分配
    print("步骤7: 验证最终打印机")
    print(f"  标签应该发送到: {printer_name}")
    print(f"  系统默认打印机: {get_printers()[0].get('name') if get_printers() else '未知'}")
    
    if result.get('success'):
        print("  ✅ 打印任务已成功提交")
    else:
        print("  ❌ 打印任务提交失败")

if __name__ == "__main__":
    debug_label_print()
