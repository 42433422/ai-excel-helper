#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面打印机诊断工具
"""

import os
import sys
import win32print
import win32api
import subprocess
import tempfile
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger(__name__)

def diagnose_printers():
    """
    全面诊断打印机系统
    """
    print("=" * 60)
    print("🖨️  打印机系统全面诊断")
    print("=" * 60)
    
    # 1. 系统打印机列表
    print("\n📋 1. 系统打印机列表:")
    try:
        all_printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
        print(f"   找到 {len(all_printers)} 个打印机:")
        
        for i, printer_info in enumerate(all_printers, 1):
            if isinstance(printer_info, tuple) and len(printer_info) >= 2:
                printer_name = printer_info[2] if len(printer_info) > 2 else printer_info[1]
                print(f"   {i}. {printer_name}")
                
                # 获取默认打印机
                try:
                    default_printer = win32print.GetDefaultPrinter()
                    if printer_name == default_printer:
                        print(f"      ⭐ 系统默认打印机")
                except:
                    pass
            else:
                print(f"   {i}. {printer_info}")
    except Exception as e:
        print(f"   ❌ 获取打印机列表失败: {e}")
    
    # 2. 打印机详细信息
    print("\n🔍 2. 打印机详细信息:")
    try:
        all_printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
        
        for i, printer_info in enumerate(all_printers, 1):
            if isinstance(printer_info, tuple) and len(printer_info) >= 2:
                printer_name = printer_info[2] if len(printer_info) > 2 else printer_info[1]
                print(f"\n   {i}. {printer_name}")
                
                try:
                    hprinter = win32print.OpenPrinter(printer_name)
                    printer_info2 = win32print.GetPrinter(hprinter, 2)
                    
                    print(f"      状态: {printer_info2.get('Status', '未知')}")
                    print(f"      端口: {printer_info2.get('PortName', '未知')}")
                    print(f"      驱动: {printer_info2.get('DriverName', '未知')}")
                    print(f"      位置: {printer_info2.get('Location', '未知')}")
                    print(f"      注释: {printer_info2.get('Comment', '无')}")
                    
                    win32print.ClosePrinter(hprinter)
                except Exception as e:
                    print(f"      ❌ 无法获取详细信息: {e}")
    except Exception as e:
        print(f"   ❌ 获取详细信息失败: {e}")
    
    # 3. 专门检查TSC TTP-244
    print("\n🏷️  3. TSC TTP-244 Plus 专门检查:")
    try:
        found_tsc = False
        all_printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
        
        for printer_info in all_printers:
            if isinstance(printer_info, tuple) and len(printer_info) >= 2:
                printer_name = printer_info[2] if len(printer_info) > 2 else printer_info[1]
                
                if 'TSC TTP-244' in printer_name or 'TTP-244' in printer_name:
                    found_tsc = True
                    print(f"   ✅ 找到TSC打印机: {printer_name}")
                    
                    # 详细检查TSC
                    try:
                        hprinter = win32print.OpenPrinter(printer_name)
                        printer_info2 = win32print.GetPrinter(hprinter, 2)
                        
                        print(f"      状态: {printer_info2.get('Status', '未知')}")
                        print(f"      端口: {printer_info2.get('PortName', '未知')}")
                        print(f"      驱动: {printer_info2.get('DriverName', '未知')}")
                        print(f"      位置: {printer_info2.get('Location', '未知')}")
                        print(f"      注释: {printer_info2.get('Comment', '无')}")
                        
                        # 测试打印机状态
                        status = printer_info2.get('Status', 0)
                        if status == 0:
                            print(f"      ✅ 打印机就绪")
                        else:
                            print(f"      ⚠️  状态码: {status}")
                        
                        win32print.ClosePrinter(hprinter)
                        
                        # 测试打印功能
                        print(f"\n      🧪 测试打印功能:")
                        test_print(printer_name)
                        
                    except Exception as e:
                        print(f"      ❌ 无法检查TSC打印机: {e}")
                    break
        
        if not found_tsc:
            print("   ❌ 未找到TSC TTP-244 Plus打印机")
    except Exception as e:
        print(f"   ❌ 检查TSC打印机失败: {e}")
    
    # 4. 打印测试
    print("\n🧪 4. 打印测试:")
    try:
        all_printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
        
        for printer_info in all_printers:
            if isinstance(printer_info, tuple) and len(printer_info) >= 2:
                printer_name = printer_info[2] if len(printer_info) > 2 else printer_info[1]
                print(f"\n   测试打印机: {printer_name}")
                test_print(printer_name)
                
    except Exception as e:
        print(f"   ❌ 打印测试失败: {e}")
    
    # 5. 系统建议
    print("\n💡 5. 系统建议:")
    print("   根据诊断结果，建议:")
    print("   1. 检查打印机驱动程序是否正确安装")
    print("   2. 确认打印机是否在线")
    print("   3. 检查打印队列是否有积压任务")
    print("   4. 重新启动打印服务")
    print("   5. 检查打印机端口配置")

def test_print(printer_name):
    """
    测试打印机功能
    """
    try:
        # 创建测试文件（使用英文避免编码问题）
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(f"Printer Test: {printer_name}\n")
            f.write("This is a test page\n")
            f.write("If you see this content, printer is working normally\n")
            test_file = f.name
        
        print(f"      创建测试文件: {test_file}")
        
        # 使用ShellExecute测试打印
        result = win32api.ShellExecute(
            0,
            "print",
            test_file,
            f'/d:"{printer_name}"',
            ".",
            0
        )
        
        if result > 32:
            print(f"      ✅ 测试文件已发送到打印机")
        else:
            print(f"      ❌ ShellExecute失败，错误码: {result}")
        
        # 清理测试文件
        try:
            os.unlink(test_file)
        except:
            pass
            
    except Exception as e:
        print(f"      ❌ 测试打印失败: {e}")

def main():
    """
    主函数
    """
    print("开始全面打印机诊断...")
    diagnose_printers()
    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
