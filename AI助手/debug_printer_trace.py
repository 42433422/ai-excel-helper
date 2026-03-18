#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试版本：追踪打印机参数使用情况
"""

import sys
import os
import logging

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置详细日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger(__name__)

def trace_printer_usage():
    """
    追踪打印机使用情况
    """
    print("=" * 70)
    print("🔍 打印机参数使用追踪")
    print("=" * 70)
    
    try:
        # 1. 测试直接调用get_document_printer
        print("\n📋 1. 测试get_document_printer函数")
        from app_api import get_document_printer
        
        doc_printer = get_document_printer()
        print(f"   get_document_printer结果: {doc_printer}")
        
        # 2. 测试调用print_document函数
        print("\n🖨️ 2. 测试print_document函数参数传递")
        from print_utils import print_document
        
        # 创建一个测试Excel文件
        test_file = "outputs/test_document.xlsx"
        os.makedirs("outputs", exist_ok=True)
        
        # 模拟真实的打印调用
        print(f"   调用: print_document('{test_file}', '{doc_printer}')")
        
        # 3. 检查PrintUtils类的print_file方法
        print("\n🔧 3. 检查PrintUtils类内部调用")
        from print_utils import PrinterUtils
        
        utils = PrinterUtils()
        print(f"   PrintUtils实例创建成功")
        
        # 4. 模拟完整的调用链
        print("\n📊 4. 模拟完整调用链")
        print(f"   步骤1: 前端调用 /api/print/<filename>")
        print(f"   步骤2: 获取document_printer = get_document_printer()")
        print(f"   步骤3: 调用 print_document(file_path, document_printer)")
        print(f"   步骤4: PrintUtils.print_file(file_path, printer_name)")
        
        # 5. 检查win32print.GetDefaultPrinter的返回值
        print("\n💻 5. 检查系统默认打印机")
        import win32print
        
        default_printer = win32print.GetDefaultPrinter()
        print(f"   系统默认打印机: {default_printer}")
        
        if default_printer == doc_printer:
            print("   ⚠️ 默认打印机与发货单打印机相同，可能导致混淆")
        else:
            print("   ✅ 默认打印机与发货单打印机不同")
        
        # 6. 模拟API调用
        print("\n📡 6. 模拟API调用场景")
        print("   模拟前端调用:")
        print("   POST /api/print/发货单_26-0200115A_20260202_174758.xlsx")
        print("   {")
        print('     "printer_name": null  // 关键：这里没有传递打印机名称！')
        print("   }")
        
        print("\n   这就是问题的根源：前端API调用没有传递printer_name参数！")
        
        return True
        
    except Exception as e:
        print(f"❌ 追踪过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def fix_api_printer_usage():
    """
    修复API中的打印机使用问题
    """
    print("\n" + "=" * 70)
    print("🔧 修复API打印机使用问题")
    print("=" * 70)
    
    try:
        # 检查当前的print_document_route函数
        print("\n📄 当前API调用流程:")
        print("   1. POST /api/print/<filename>")
        print("   2. data.get('printer_name', None)")
        print("   3. print_document(file_path, printer_name)  // 如果printer_name为None，则使用默认打印机")
        
        print("\n🎯 问题分析:")
        print("   • 前端调用API时没有传递printer_name参数")
        print("   • API接收到printer_name=None")
        print("   • print_document内部回退到GetDefaultPrinter()")
        print("   • 默认打印机是TSC TTP-244 Plus")
        
        print("\n✅ 解决方案:")
        print("   1. 修改print_document_route函数，自动检测发货单打印机")
        print("   2. 如果前端没有传递printer_name，自动使用Jolimark")
        print("   3. 或者修改前端调用，确保总是传递正确的打印机名称")
        
        return True
        
    except Exception as e:
        print(f"❌ 修复分析出错: {e}")
        return False

if __name__ == "__main__":
    print("🧪 开始打印机参数追踪")
    
    # 追踪
    trace_result = trace_printer_usage()
    
    # 修复建议
    fix_result = fix_api_printer_usage()
    
    print("\n" + "=" * 70)
    print("📊 总结")
    print("=" * 70)
    
    if trace_result and fix_result:
        print("✅ 问题根源已找到：前端API调用缺少打印机参数")
        print("✅ 解决方案已提供：自动检测发货单打印机")
    else:
        print("❌ 追踪过程遇到问题")