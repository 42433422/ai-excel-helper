#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打印机信息诊断脚本
检查前端显示、后端获取、实际打印机之间的差异
"""

import os
import sys
import json
import time
import win32print
import win32api

def diagnose_printer_info():
    """诊断打印机信息的一致性问题"""
    print("=" * 80)
    print("🔍 打印机信息诊断")
    print("=" * 80)
    
    try:
        # 1. 获取实际系统打印机信息
        print("\n📋 1. 获取实际系统打印机信息")
        print("-" * 80)
        
        # 获取Windows默认打印机
        try:
            windows_default = win32print.GetDefaultPrinter()
            print(f"✅ Windows默认打印机: {windows_default}")
        except Exception as e:
            print(f"❌ 获取Windows默认打印机失败: {e}")
            windows_default = None
        
        # 获取所有本地打印机
        try:
            printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)
            print(f"✅ 找到 {len(printers)} 个本地打印机:")
            
            for i, printer in enumerate(printers):
                printer_name = printer[2]
                printer_info = printer[1]
                printer_flags = printer[0]
                
                # 获取打印机详细状态
                try:
                    hPrinter = win32print.OpenPrinter(printer_name)
                    job_count = len(win32print.EnumJobs(hPrinter, 0, -1, 1))
                    win32print.ClosePrinter(hPrinter)
                except:
                    job_count = "N/A"
                
                # 判断是否默认打印机
                is_default = "✓ 默认" if printer_name == windows_default else ""
                
                print(f"   {i+1}. {printer_name} {is_default}")
                print(f"      状态: {job_count} 个作业")
                print(f"      标志: {printer_flags}")
                print(f"      信息: {printer_info[:50]}...")
                
        except Exception as e:
            print(f"❌ 获取打印机列表失败: {e}")
        
        # 2. 模拟后端打印机识别逻辑
        print("\n" + "=" * 80)
        print("📋 2. 模拟后端打印机识别逻辑")
        print("-" * 80)
        
        # 识别发货单打印机
        doc_printer_keywords = ['joli', '24-pin', 'epson', 'canon', 'hp', 'laser', 'inkjet', '点阵', '针式']
        label_printer_keywords = ['tsc', 'ttp', 'label', '条码', 'thermal', 'zebra']
        
        detected_doc_printer = None
        detected_label_printer = None
        
        for printer in printers:
            printer_name = printer[2].lower()
            
            # 识别发货单打印机
            if not detected_doc_printer:
                if any(keyword in printer_name for keyword in doc_printer_keywords):
                    detected_doc_printer = printer[2]
                    print(f"✅ 识别为发货单打印机: {detected_doc_printer}")
            
            # 识别标签打印机
            if not detected_label_printer:
                if any(keyword in printer_name for keyword in label_printer_keywords):
                    detected_label_printer = printer[2]
                    print(f"✅ 识别为标签打印机: {detected_label_printer}")
        
        # 如果没有识别到，尝试使用第二个打印机
        if not detected_doc_printer and printers:
            detected_doc_printer = printers[0][2]
            print(f"⚠️ 未识别到发货单打印机，使用第一个: {detected_doc_printer}")
        
        if not detected_label_printer and len(printers) > 1:
            detected_label_printer = printers[1][2]
            print(f"⚠️ 未识别到标签打印机，使用第二个: {detected_label_printer}")
        elif not detected_label_printer:
            detected_label_printer = detected_doc_printer
            print(f"⚠️ 未识别到标签打印机，临时使用发货单打印机: {detected_label_printer}")
        
        # 3. 检查打印机冲突
        print("\n" + "=" * 80)
        print("📋 3. 检查打印机分配")
        print("-" * 80)
        
        if detected_doc_printer == detected_label_printer:
            print(f"❌ 错误: 发货单和标签打印机相同: {detected_doc_printer}")
            print("💡 建议: 确保系统中有至少两个不同的打印机")
        else:
            print(f"✅ 打印机分配正确:")
            print(f"   📄 发货单打印机: {detected_doc_printer}")
            print(f"   🏷️ 标签打印机: {detected_label_printer}")
        
        # 4. 模拟前端显示的打印机信息
        print("\n" + "=" * 80)
        print("📋 4. 前端显示的打印机信息（模拟）")
        print("-" * 80)
        
        frontend_display = {
            "default_printer": windows_default,
            "all_printers": [p[2] for p in printers],
            "document_printer": detected_doc_printer,
            "label_printer": detected_label_printer
        }
        
        print(f"前端应该显示的信息:")
        print(json.dumps(frontend_display, ensure_ascii=False, indent=2))
        
        # 5. 对比分析
        print("\n" + "=" * 80)
        print("📋 5. 对比分析")
        print("-" * 80)
        
        print("系统实际状态 vs 后端识别 vs 前端显示:")
        print(f"  Windows默认打印机: {windows_default}")
        print(f"  后端发货单打印机: {detected_doc_printer}")
        print(f"  后端标签打印机: {detected_label_printer}")
        
        # 检查是否一致
        if windows_default == detected_doc_printer:
            print("✅ 默认打印机与发货单打印机一致")
        else:
            print("⚠️ 默认打印机与发货单打印机不一致")
            print("💡 建议: 考虑将发货单打印机设为Windows默认打印机")
        
        if detected_doc_printer == detected_label_printer:
            print("❌ 错误: 发货单和标签打印机相同")
        else:
            print("✅ 发货单和标签打印机不同")
        
        # 6. 建议
        print("\n" + "=" * 80)
        print("💡 建议")
        print("=" * 80)
        
        if windows_default != detected_doc_printer:
            print("1. 考虑将发货单打印机设为Windows默认打印机")
            print(f"   命令: rundll32 printui.dll,PrintUIEntry /y /n \"{detected_doc_printer}\"")
        
        if detected_doc_printer == detected_label_printer:
            print("2. 确保系统中有至少两个不同的打印机")
            print("   当前发货单和标签使用同一台打印机")
        
        print("\n3. 检查打印机连接状态")
        print("   确保两台打印机都已连接并就绪")
        
        print("\n4. 如果问题仍然存在")
        print("   - 检查前端代码是否正确显示打印机信息")
        print("   - 检查后端API是否正确返回打印机信息")
        print("   - 验证网络通信是否正常")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 诊断过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_printer_connection():
    """测试打印机连接状态"""
    print("\n" + "=" * 80)
    print("🔌 测试打印机连接状态")
    print("=" * 80)
    
    try:
        printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)
        
        for printer in printers:
            printer_name = printer[2]
            print(f"\n测试打印机: {printer_name}")
            
            # 尝试打开打印机
            try:
                hPrinter = win32print.OpenPrinter(printer_name)
                
                # 获取打印机状态
                printer_status = win32print.GetPrinter(hPrinter, 2)
                status = printer_status.get('Status', 'Unknown')
                print(f"   状态代码: {status}")
                
                # 解释状态
                status_map = {
                    0: "就绪",
                    1: "暂停",
                    2: "错误",
                    4: "正在删除",
                    8: "纸张用尽",
                    16: "手动送纸",
                    32: "打印机无联机",
                    64: "处理中",
                    128: "页间出纸",
                    256: "打印机无响应",
                    512: "忙",
                    1024: "打印机处于只读模式"
                }
                
                status_text = status_map.get(status, f"未知状态({status})")
                print(f"   状态: {status_text}")
                
                # 获取作业数量
                jobs = win32print.EnumJobs(hPrinter, 0, -1, 1)
                print(f"   当前作业数: {len(jobs)}")
                
                win32print.ClosePrinter(hPrinter)
                print(f"   ✅ 打印机连接正常")
                
            except Exception as e:
                print(f"   ❌ 打印机连接失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试打印机连接失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始打印机信息诊断...")
    
    # 运行诊断
    diagnose_success = diagnose_printer_info()
    test_success = test_printer_connection()
    
    print("\n" + "=" * 80)
    print("🎉 诊断完成")
    print("=" * 80)
    
    if diagnose_success:
        print("✅ 打印机信息诊断完成")
    else:
        print("❌ 打印机信息诊断失败")
    
    if test_success:
        print("✅ 打印机连接测试完成")
    else:
        print("❌ 打印机连接测试失败")
    
    print("\n💡 根据诊断结果采取相应措施:")
    print("   1. 如果打印机状态异常，重启打印机或重新连接")
    print("   2. 如果打印机分配错误，检查打印机识别逻辑")
    print("   3. 如果信息显示不一致，检查前端和后端代码")
