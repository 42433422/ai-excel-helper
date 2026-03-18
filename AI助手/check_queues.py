#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查当前打印机队列状态
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_printer_queues():
    """检查打印机队列状态"""
    print("=" * 60)
    print("📋 检查当前打印机队列状态")
    print("=" * 60)
    
    try:
        import win32print
        
        # 获取所有打印机
        printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)
        print(f"\n找到 {len(printers)} 个打印机:")
        for i, printer in enumerate(printers):
            print(f"{i+1}. {printer[2]}")
        
        # 检查TSC TTP-244 Plus
        print("\n" + "=" * 60)
        print("🏷️ TSC TTP-244 Plus 队列状态")
        print("=" * 60)
        try:
            hPrinter = win32print.OpenPrinter("TSC TTP-244 Plus")
            jobs = win32print.EnumJobs(hPrinter, 0, -1, 1)
            win32print.ClosePrinter(hPrinter)
            
            if jobs:
                print(f"有 {len(jobs)} 个打印任务:")
                for job in jobs:
                    print(f"  - 作业ID: {job['JobId']}")
                    print(f"    文档: {job.get('pDocument', 'Unknown')}")
                    print(f"    状态: {job.get('Status', 'Unknown')}")
                    print(f"    提交时间: {job.get('Submitted', 'Unknown')}")
            else:
                print("队列为空")
                
        except Exception as e:
            print(f"❌ TSC打印机检查失败: {e}")
        
        # 检查Jolimark 24-pin printer
        print("\n" + "=" * 60)
        print("📄 Jolimark 24-pin printer 队列状态")
        print("=" * 60)
        try:
            hPrinter = win32print.OpenPrinter("Jolimark 24-pin printer")
            jobs = win32print.EnumJobs(hPrinter, 0, -1, 1)
            win32print.ClosePrinter(hPrinter)
            
            if jobs:
                print(f"有 {len(jobs)} 个打印任务:")
                for job in jobs:
                    print(f"  - 作业ID: {job['JobId']}")
                    print(f"    文档: {job.get('pDocument', 'Unknown')}")
                    print(f"    状态: {job.get('Status', 'Unknown')}")
                    print(f"    提交时间: {job.get('Submitted', 'Unknown')}")
            else:
                print("队列为空")
                
        except Exception as e:
            print(f"❌ Jolimark打印机检查失败: {e}")
        
        # 检查默认打印机
        print("\n" + "=" * 60)
        print("🎯 Windows默认打印机")
        print("=" * 60)
        try:
            default_printer = win32print.GetDefaultPrinter()
            print(f"当前默认打印机: {default_printer}")
        except Exception as e:
            print(f"❌ 获取默认打印机失败: {e}")
            
        # 分析问题
        print("\n" + "=" * 60)
        print("🔍 问题分析")
        print("=" * 60)
        
        tsc_has_jobs = False
        jolimark_has_jobs = False
        
        try:
            hPrinter = win32print.OpenPrinter("TSC TTP-244 Plus")
            jobs = win32print.EnumJobs(hPrinter, 0, -1, 1)
            win32print.ClosePrinter(hPrinter)
            tsc_has_jobs = len(jobs) > 0
        except:
            pass
            
        try:
            hPrinter = win32print.OpenPrinter("Jolimark 24-pin printer")
            jobs = win32print.EnumJobs(hPrinter, 0, -1, 1)
            win32print.ClosePrinter(hPrinter)
            jolimark_has_jobs = len(jobs) > 0
        except:
            pass
        
        if not tsc_has_jobs and not jolimark_has_jobs:
            print("❌ 两个打印机的队列都是空的")
            print("💡 可能的原因:")
            print("   1. 打印任务已完成或被取消")
            print("   2. 我修改的代码影响了任务发送")
            print("   3. 系统清理了打印队列")
        elif tsc_has_jobs and not jolimark_has_jobs:
            print("✅ TSC打印机有任务，Jolimark打印机为空（正常）")
        elif not tsc_has_jobs and jolimark_has_jobs:
            print("❌ 只有Jolimark打印机有任务（标签被发送到发货单打印机）")
        else:
            print("⚠️ 两台打印机都有任务")
        
        return tsc_has_jobs, jolimark_has_jobs
        
    except Exception as e:
        print(f"❌ 检查过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False, False

if __name__ == "__main__":
    tsc_jobs, jolimark_jobs = check_printer_queues()
    print("\n" + "=" * 60)
    print("📊 总结")
    print("=" * 60)
    print(f"TSC TTP-244 Plus: {'有任务' if tsc_jobs else '无任务'}")
    print(f"Jolimark 24-pin printer: {'有任务' if jolimark_jobs else '无任务'}")
