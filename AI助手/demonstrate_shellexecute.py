#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
演示ShellExecute在打印系统中的工作原理
"""

import os
import win32api
import win32print
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger(__name__)

def demonstrate_shellexecute():
    """
    演示ShellExecute的两种工作模式
    """
    print("=" * 60)
    print("🔧 ShellExecute 打印工作原理演示")
    print("=" * 60)
    
    # 获取打印机列表
    printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
    label_printer = None
    for printer in printers:
        if 'TSC' in str(printer) or 'TTP' in str(printer):
            label_printer = printer[2] if len(printer) > 2 else printer[1]
            break
    
    if not label_printer:
        label_printer = printers[0][2] if printers else "Microsoft Print to PDF"
    
    print(f"目标打印机: {label_printer}")
    print()
    
    # 创建一个测试文件
    test_file = "shell_execute_test.txt"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write("ShellExecute 测试文件\n")
        f.write("=" * 30 + "\n")
        f.write("这是ShellExecute函数演示文件\n")
        f.write("如果看到此内容，说明打印功能正常\n")
        f.write(f"测试时间: 2026-02-02\n")
    
    print(f"1. 创建测试文件: {test_file}")
    
    # 方法1: "printto" 模式 - 直接发送到打印机队列
    print("\n2. 测试 'printto' 模式...")
    try:
        result1 = win32api.ShellExecute(
            0,                    # 父窗口句柄
            "printto",           # 操作类型
            test_file,           # 文件路径
            f'"{label_printer}"', # 打印机名称（用引号包围）
            ".",                 # 工作目录
            0                    # 隐藏窗口
        )
        
        if result1 > 32:
            print(f"✅ 'printto' 模式成功")
            print(f"   返回码: {result1}")
            print(f"   特点: 直接发送到打印机队列，不打开应用程序")
        else:
            print(f"❌ 'printto' 模式失败")
            print(f"   错误码: {result1}")
            
    except Exception as e:
        print(f"❌ 'printto' 模式异常: {e}")
    
    # 等待一下
    import time
    time.sleep(2)
    
    # 方法2: "print" 模式 - 使用系统默认处理
    print("\n3. 测试 'print' 模式...")
    try:
        result2 = win32api.ShellExecute(
            0,
            "print",
            test_file,
            f'/d:"{label_printer}"',  # 使用/d参数指定打印机
            ".",
            0
        )
        
        if result2 > 32:
            print(f"✅ 'print' 模式成功")
            print(f"   返回码: {result2}")
            print(f"   特点: 使用系统默认应用程序处理")
        else:
            print(f"❌ 'print' 模式失败")
            print(f"   错误码: {result2}")
            
    except Exception as e:
        print(f"❌ 'print' 模式异常: {e}")
    
    # 清理测试文件
    try:
        os.remove(test_file)
        print(f"\n4. 清理测试文件: {test_file}")
    except:
        pass
    
    print("\n" + "=" * 60)
    print("📊 ShellExecute 工作原理总结")
    print("=" * 60)
    print("1. ShellExecute是Windows API函数，告诉系统'请打印这个文件'")
    print("2. 系统根据文件类型找到对应的默认应用程序")
    print("3. 应用程序将文件发送到指定的打印机队列")
    print("4. 打印机在后台处理打印任务")
    print("5. 返回码 > 32 表示成功，<= 32 表示各种错误")
    print("\n💡 在您的项目中:")
    print("   - print_single_label.py 使用 'printto' 模式（推荐）")
    print("   - pdf_label_printer.py 使用 'print' 模式（通用）")
    print("   - 两者都发送到 TSC TTP-244 Plus 标签打印机")

if __name__ == "__main__":
    demonstrate_shellexecute()