#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打印机解决方案工具
解决Windows默认打印机冲突问题
"""

import sys
import os
import win32print
import win32con
import time

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def solve_printer_conflicts():
    """解决打印机冲突问题"""
    print("=" * 80)
    print("🛠️ 打印机冲突解决方案")
    print("=" * 80)
    
    try:
        # 1. 分析当前打印机状态
        print("\n🔍 1. 分析当前打印机状态")
        printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)
        
        current_default = None
        printer_status = {}
        
        for i, printer in enumerate(printers, 1):
            printer_name = printer[2]
            print(f"\n   📄 打印机 {i}: {printer_name}")
            
            try:
                hPrinter = win32print.OpenPrinter(printer_name)
                printer_info = win32print.GetPrinter(hPrinter, 2)
                
                # 检查是否为默认打印机
                attributes = printer_info.get('Attributes', 0)
                is_default = bool(attributes & 0x00000004)  # PRINTER_ATTRIBUTE_DEFAULT
                
                if is_default:
                    current_default = printer_name
                    print(f"      ✅ 是Windows默认打印机")
                else:
                    print(f"      📄 不是默认打印机")
                
                # 记录状态
                printer_status[printer_name] = {
                    'is_default': is_default,
                    'status': printer_info.get('Status', '未知'),
                    'attributes': attributes
                }
                
                win32print.ClosePrinter(hPrinter)
                
            except Exception as e:
                print(f"      ❌ 无法检查状态: {e}")
        
        print(f"\n   🎯 当前Windows默认打印机: {current_default}")
        
        # 2. 检查队列状况
        print("\n📋 2. 检查打印机队列状况")
        for printer_name in printer_status.keys():
            print(f"\n   📋 {printer_name}")
            try:
                hPrinter = win32print.OpenPrinter(printer_name)
                jobs = win32print.EnumJobs(hPrinter, 0, -1, 1)
                
                if jobs:
                    print(f"      ⚠️ 有 {len(jobs)} 个作业等待中:")
                    for job in jobs:
                        print(f"         - 作业ID: {job['JobId']}, 文档: {job.get('pDocument', '未知')}")
                else:
                    print(f"      ✅ 队列为空")
                
                win32print.ClosePrinter(hPrinter)
                
            except Exception as e:
                print(f"      ❌ 无法检查队列: {e}")
        
        # 3. 解决冲突策略
        print("\n🛠️ 3. 解决冲突策略")
        
        if current_default == 'Jolimark 24-pin printer':
            print("   🔍 检测到问题：Jolimark是Windows默认打印机")
            print("   💡 建议解决方案:")
            print("      方案1: 临时更改Windows默认打印机")
            print("      方案2: 使用明确的打印机句柄而非默认打印机")
            print("      方案3: 清空队列后重新配置")
            
            # 询问用户选择
            print("\n   🤔 您希望如何解决？")
            print("   1) 临时更改Windows默认打印机为TSC")
            print("   2) 只在程序运行时临时切换默认打印机")
            print("   3) 清空当前队列")
            print("   4) 查看详细分析")
            
        elif current_default == 'TSC TTP-244 Plus':
            print("   🔍 检测到问题：TSC是Windows默认打印机")
            print("   💡 建议解决方案:")
            print("      方案1: 临时更改Windows默认打印机为Jolimark")
            print("      方案2: 使用明确的打印机句柄而非默认打印机")
            
        else:
            print("   ✅ Windows默认打印机不是Jolimark或TSC")
            print("   💡 建议：检查程序是否正确使用了指定的打印机")
        
        # 4. 提供解决脚本
        print("\n📜 4. 解决脚本")
        
        # 临时更改默认打印机脚本
        print("\n   📝 临时更改Windows默认打印机脚本:")
        if current_default == 'TSC TTP-244 Plus':
            print("""
@echo off
echo 临时更改Windows默认打印机为Jolimark
rundll32 printui.dll,PrintUIEntry /y /n "Jolimark 24-pin printer"
echo 默认打印机已更改
pause
            """)
        else:
            print("""
@echo off
echo 临时更改Windows默认打印机为TSC
rundll32 printui.dll,PrintUIEntry /y /n "TSC TTP-244 Plus"
echo 默认打印机已更改
pause
            """)
        
        # 恢复默认打印机脚本
        print("\n   📝 恢复默认打印机脚本:")
        print("""
@echo off
echo 恢复Windows默认打印机设置
rundll32 printui.dll,PrintUIEntry /y /n "Microsoft Print to PDF"
echo 默认打印机已恢复
pause
        """)
        
        return True
        
    except Exception as e:
        print(f"❌ 解决方案分析失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def clear_printer_queue(printer_name):
    """清空打印机队列"""
    try:
        hPrinter = win32print.OpenPrinter(printer_name)
        jobs = win32print.EnumJobs(hPrinter, 0, -1, 1)
        
        if jobs:
            print(f"清空 {printer_name} 队列中的 {len(jobs)} 个作业...")
            for job in jobs:
                try:
                    win32print.SetJob(hPrinter, job['JobId'], 0, None, win32print.JOB_CONTROL_CANCEL)
                except Exception as e:
                    print(f"无法取消作业 {job['JobId']}: {e}")
        
        win32print.ClosePrinter(hPrinter)
        return True
        
    except Exception as e:
        print(f"清空队列失败: {e}")
        return False

def change_default_printer(printer_name):
    """更改Windows默认打印机"""
    try:
        print(f"正在更改Windows默认打印机为: {printer_name}")
        
        # 使用PrintUI更改默认打印机
        import subprocess
        result = subprocess.run([
            'rundll32', 'printui.dll,PrintUIEntry', 
            '/y', '/n', printer_name
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ 成功更改默认打印机为: {printer_name}")
            return True
        else:
            print(f"❌ 更改默认打印机失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"更改默认打印机失败: {e}")
        return False

if __name__ == "__main__":
    solve_printer_conflicts()
