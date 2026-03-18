#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速验证打印机修复是否有效
"""

import sys
import os
import win32print
import time

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_enhanced_pdf_printing():
    """测试增强的PDF打印功能"""
    print("=" * 80)
    print("🧪 快速验证打印机修复")
    print("=" * 80)
    
    try:
        # 1. 检查当前默认打印机
        print("\n📋 1. 检查当前默认打印机")
        current_default = win32print.GetDefaultPrinter()
        print(f"   当前默认打印机: {current_default}")
        
        # 2. 检查PDF文件
        print("\n📄 2. 检查PDF文件")
        pdf_files = [
            "PDF文件/订单26-0200123A_标签.pdf",
            "PDF文件/商标标签完整版.pdf",
        ]
        
        pdf_path = None
        for file in pdf_files:
            if os.path.exists(file):
                pdf_path = file
                print(f"   ✅ 找到PDF文件: {file}")
                break
        
        if not pdf_path:
            print("   ❌ 未找到PDF文件")
            return False
        
        # 3. 测试增强的PDF打印
        print("\n🧪 3. 测试增强的PDF打印")
        from special_trademark_print import print_trademark_pdf
        
        print(f"   📄 测试文件: {pdf_path}")
        print(f"   🎯 目标打印机: TSC TTP-244 Plus")
        print(f"   💡 预期结果: 发送到TSC而不是Jolimark")
        
        # 执行测试
        result = print_trademark_pdf(pdf_path, "TSC TTP-244 Plus", show_app=True)
        
        print(f"\n   📊 测试结果:")
        print(f"   成功: {result.get('success', False)}")
        print(f"   方法: {result.get('method', 'unknown')}")
        print(f"   消息: {result.get('message', 'No message')}")
        print(f"   打印机: {result.get('printer', 'unknown')}")
        
        # 4. 检查打印机队列
        print("\n📋 4. 检查打印机队列变化")
        time.sleep(3)  # 等待打印作业进入队列
        
        printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)
        for printer in printers:
            printer_name = printer[2]
            if printer_name in ["TSC TTP-244 Plus", "Jolimark 24-pin printer"]:
                print(f"\n   📋 {printer_name}:")
                try:
                    hPrinter = win32print.OpenPrinter(printer_name)
                    jobs = win32print.EnumJobs(hPrinter, 0, -1, 1)
                    
                    if jobs:
                        print(f"      📝 有 {len(jobs)} 个作业:")
                        for job in jobs:
                            doc_name = job.get('pDocument', 'Unknown')
                            print(f"         - 作业ID: {job['JobId']}, 文档: {doc_name}")
                    else:
                        print(f"      ✅ 队列为空")
                    
                    win32print.ClosePrinter(hPrinter)
                except Exception as e:
                    print(f"      ❌ 检查失败: {e}")
        
        # 5. 分析结果
        print("\n🔍 5. 结果分析")
        if result.get('success'):
            print("   ✅ PDF打印任务发送成功")
            if "TSC" in result.get('message', ''):
                print("   ✅ 目标打印机为TSC (正确)")
            elif "Jolimark" in result.get('message', ''):
                print("   ❌ 目标打印机为Jolimark (错误)")
            else:
                print("   ❓ 打印机确认信息不明确")
        else:
            print("   ❌ PDF打印任务发送失败")
        
        return result.get('success', False)
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def quick_test():
    """快速测试"""
    print("🚀 快速验证打印机修复...")
    
    success = test_enhanced_pdf_printing()
    
    print("\n" + "=" * 80)
    print("📊 总结:")
    if success:
        print("✅ 打印机修复成功！标签现在应该发送到TSC打印机")
    else:
        print("❌ 打印机修复可能还需要进一步调试")
    print("=" * 80)

if __name__ == "__main__":
    quick_test()
