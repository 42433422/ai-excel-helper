#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证调用应用时明确指定打印机的改进效果
"""

import sys
import os
import win32print
import time

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_app_printer_specification():
    """测试调用应用时明确指定打印机的效果"""
    print("=" * 80)
    print("🎯 验证调用应用时明确指定打印机")
    print("=" * 80)
    
    try:
        # 1. 检查PDF文件
        print("\n📄 1. 检查PDF文件")
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
        
        # 2. 记录测试前的队列状态
        print("\n📋 2. 记录测试前的打印机队列状态")
        
        def check_queue(printer_name):
            try:
                hPrinter = win32print.OpenPrinter(printer_name)
                jobs = win32print.EnumJobs(hPrinter, 0, -1, 1)
                win32print.ClosePrinter(hPrinter)
                return len(jobs)
            except:
                return -1
        
        initial_tsc_queue = check_queue("TSC TTP-244 Plus")
        initial_jolimark_queue = check_queue("Jolimark 24-pin printer")
        
        print(f"   TSC TTP-244 Plus 队列: {initial_tsc_queue} 个作业")
        print(f"   Jolimark 24-pin printer 队列: {initial_jolimark_queue} 个作业")
        
        # 3. 测试改进的PDF打印
        print("\n🎯 3. 测试改进的PDF打印")
        from special_trademark_print import print_trademark_pdf
        
        print(f"   📄 测试文件: {pdf_path}")
        print(f"   🖨️ 明确指定打印机: TSC TTP-244 Plus")
        print(f"   💡 关键改进: 在调用PDF应用时直接包含打印机参数")
        print(f"   📝 预期: PDF应用一启动就知道要使用TSC打印机")
        
        # 执行测试（显示应用窗口以便观察）
        result = print_trademark_pdf(pdf_path, "TSC TTP-244 Plus", show_app=True)
        
        print(f"\n   📊 打印结果:")
        print(f"   ✅ 成功: {result.get('success', False)}")
        print(f"   🔧 方法: {result.get('method', 'unknown')}")
        print(f"   📝 消息: {result.get('message', 'No message')}")
        print(f"   🖨️ 目标打印机: {result.get('printer', 'unknown')}")
        
        # 4. 检查队列变化
        print("\n📋 4. 检查打印队列变化")
        time.sleep(3)  # 等待打印作业进入队列
        
        final_tsc_queue = check_queue("TSC TTP-244 Plus")
        final_jolimark_queue = check_queue("Jolimark 24-pin printer")
        
        print(f"   TSC TTP-244 Plus 队列: {initial_tsc_queue} → {final_tsc_queue} (变化: {final_tsc_queue - initial_tsc_queue})")
        print(f"   Jolimark 24-pin printer 队列: {initial_jolimark_queue} → {final_jolimark_queue} (变化: {final_jolimark_queue - initial_jolimark_queue})")
        
        # 5. 分析结果
        print("\n🔍 5. 结果分析")
        print("   改进要点:")
        print("   ✅ 在调用PDF应用时就明确指定打印机")
        print("   ✅ 参数格式: '文件路径' /d:'打印机名称'")
        print("   ✅ PDF应用一启动就知道使用哪个打印机")
        
        if result.get('success'):
            print("\n   ✅ 打印任务发送成功")
            
            # 判断任务是否发送到正确打印机
            tsc_increased = final_tsc_queue > initial_tsc_queue
            jolimark_increased = final_jolimark_queue > initial_jolimark_queue
            
            if tsc_increased and not jolimark_increased:
                print("   🎉 完美！标签任务发送到TSC打印机（正确）")
                return True
            elif jolimark_increased and not tsc_increased:
                print("   ❌ 标签任务仍发送到Jolimark打印机（需要进一步调整）")
                return False
            elif tsc_increased and jolimark_increased:
                print("   ⚠️ 标签任务同时发送到两台打印机")
                return False
            else:
                print("   ❓ 无法确定任务发送状态")
                return False
        else:
            print("   ❌ 打印任务发送失败")
            return False
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def demonstrate_improvement():
    """演示改进的关键点"""
    print("\n" + "=" * 80)
    print("💡 改进说明：调用应用时明确指定打印机")
    print("=" * 80)
    
    print("\n🔧 改进前的方法:")
    print("   ShellExecute('print', '文件路径', '/d:打印机名称')")
    print("   问题: 打印机参数可能被子应用忽略")
    
    print("\n✅ 改进后的方法:")
    print("   ShellExecute('print', '\"文件路径\" /d:\"打印机名称\"')")
    print("   优势: 打印机参数直接包含在调用参数中")
    
    print("\n🎯 关键改进:")
    print("   1. 在调用PDF应用时就明确指定打印机")
    print("   2. 使用更明确的参数格式")
    print("   3. 确保PDF应用一启动就知道使用哪个打印机")

if __name__ == "__main__":
    print("🚀 开始验证调用应用时明确指定打印机的改进...")
    
    success = test_app_printer_specification()
    demonstrate_improvement()
    
    print("\n" + "=" * 80)
    print("📊 最终结果:")
    if success:
        print("🎉 改进成功！调用应用时明确指定打印机的方法有效")
        print("✅ 标签任务现在正确发送到TSC打印机")
    else:
        print("⚠️ 改进方向正确，但可能需要进一步微调参数格式")
    print("=" * 80)
