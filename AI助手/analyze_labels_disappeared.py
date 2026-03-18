#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度分析为什么标签任务不见了
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def analyze_why_labels_disappeared():
    """分析为什么标签任务不见了"""
    print("=" * 80)
    print("🔍 深度分析：为什么标签任务不见了")
    print("=" * 80)
    
    try:
        import win32print
        
        # 1. 检查当前默认打印机
        print("\n📋 1. 检查Windows默认打印机")
        current_default = win32print.GetDefaultPrinter()
        print(f"   当前默认打印机: {current_default}")
        
        # 2. 检查打印任务详情
        print("\n📊 2. 分析现有打印任务")
        try:
            hPrinter = win32print.OpenPrinter("Jolimark 24-pin printer")
            jobs = win32print.EnumJobs(hPrinter, 0, -1, 1)
            win32print.ClosePrinter(hPrinter)
            
            if jobs:
                for job in jobs:
                    print(f"   任务ID: {job['JobId']}")
                    print(f"   文档: {job.get('pDocument', 'Unknown')}")
                    print(f"   状态: {job.get('Status', 'Unknown')}")
                    print(f"   提交时间: {job.get('Submitted', 'Unknown')}")
                    print(f"   优先级: {job.get('Priority', 'Unknown')}")
                    print(f"   总字节数: {job.get('TotalBytes', 'Unknown')}")
                    print(f"   状态字符串: {job.get('StatusString', 'Unknown')}")
        except Exception as e:
            print(f"   ❌ 无法检查Jolimark任务: {e}")
        
        # 3. 测试直接ShellExecute
        print("\n🧪 3. 测试直接ShellExecute到TSC")
        import win32api
        test_file = "PDF文件\\订单26-0200123A_标签.pdf"
        abs_path = os.path.abspath(test_file)
        
        print(f"   测试文件: {abs_path}")
        print(f"   文件存在: {os.path.exists(abs_path)}")
        
        # 测试ShellExecute调用
        try:
            print(f"   目标打印机: TSC TTP-244 Plus")
            result = win32api.ShellExecute(
                0,
                "print",
                abs_path,
                '/d:"TSC TTP-244 Plus"',
                ".",
                1  # SW_SHOW 显示窗口
            )
            
            print(f"   ShellExecute结果: {result}")
            if result > 32:
                print("   ✅ ShellExecute调用成功")
            else:
                print(f"   ❌ ShellExecute失败，错误代码: {result}")
                
        except Exception as e:
            print(f"   ❌ ShellExecute测试失败: {e}")
        
        # 4. 检查PDF文件关联
        print("\n🔗 4. 检查PDF文件关联")
        try:
            import win32con
            # 检查默认PDF处理器
            result = win32api.ShellExecute(
                0,
                "open",
                abs_path,
                "",
                ".",
                1  # 只打开，不打印
            )
            
            if result > 32:
                print(f"   ✅ PDF文件可以正常打开")
            else:
                print(f"   ❌ PDF文件打开失败")
        except Exception as e:
            print(f"   ❌ PDF文件检查失败: {e}")
        
        # 5. 分析问题
        print("\n🔍 5. 问题分析")
        print("   可能的原因:")
        print("   1. Windows默认打印机设置为TSC")
        print("   2. PDF应用启动但没有立即进入打印队列")
        print("   3. 打印任务已被取消或完成")
        print("   4. 权限问题阻止打印")
        
        # 6. 提供解决方案
        print("\n🛠️ 6. 解决方案建议")
        print("   方案1: 临时将Windows默认打印机改为Jolimark")
        print("   方案2: 使用更直接的方法调用PDF应用")
        print("   方案3: 检查是否有PDF应用进程运行")
        
        # 7. 测试默认打印机设置的影响
        print("\n🎯 7. 测试默认打印机设置")
        print(f"   当前默认: {current_default}")
        print("   如果标签应该发送到TSC，但默认是TSC，这可能是正常的")
        print("   但如果标签应该发送到TSC，默认也是TSC，那可能是默认打印机机制导致的")
        
    except Exception as e:
        print(f"❌ 分析过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_why_labels_disappeared()
