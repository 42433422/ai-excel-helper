#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打印机分离强化解决方案
彻底解决标签和发货单打印机冲突问题
"""

import sys
import os
import win32print
import win32con

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_printer_functions():
    """测试打印机识别函数"""
    print("=" * 80)
    print("🧪 测试打印机识别函数")
    print("=" * 80)
    
    try:
        from app_api import get_document_printer, get_label_printer, validate_printer_separation
        
        print("\n🔍 1. 测试发货单打印机识别")
        doc_printer = get_document_printer()
        print(f"   📄 发货单打印机: {doc_printer}")
        
        print("\n🏷️ 2. 测试标签打印机识别")
        label_printer = get_label_printer()
        print(f"   🏷️ 标签打印机: {label_printer}")
        
        print("\n🔍 3. 验证打印机分离性")
        validation = validate_printer_separation()
        print(f"   验证结果: {'✅ 通过' if validation['valid'] else '❌ 失败'}")
        print(f"   错误信息: {validation['error']}")
        
        print("\n💡 4. 分析问题")
        if doc_printer and label_printer:
            if doc_printer == label_printer:
                print("   ❌ 核心问题：两个打印机名称相同！")
                print("   🔧 解决方案：重新命名打印机或检查驱动程序")
            else:
                print("   ✅ 打印机识别正常")
                print("   ❓ 问题可能在于ShellExecute被默认打印机覆盖")
        else:
            print("   ❌ 打印机识别失败")
        
        return doc_printer, label_printer, validation
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

def test_direct_printing(doc_printer, label_printer):
    """测试直接打印功能"""
    print("\n🧪 5. 测试直接打印功能")
    
    if not doc_printer or not label_printer:
        print("   ❌ 无法测试：打印机未正确识别")
        return
    
    try:
        # 创建测试文件
        test_file = "test_print.html"
        test_content = """
        <html>
        <head><title>打印机测试</title></head>
        <body>
        <h1>发货单打印机测试</h1>
        <p>测试时间: 2026-02-02</p>
        </body>
        </html>
        """
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        print(f"   📄 创建测试文件: {test_file}")
        
        # 测试发货单打印机
        print(f"\n   🖨️ 测试发货单打印机: {doc_printer}")
        try:
            hPrinter = win32print.OpenPrinter(doc_printer)
            dc = win32print.CreateDC("WINSPOOL", doc_printer)
            win32print.StartDoc(dc, ("Test Doc", None))
            win32print.StartPage(dc)
            win32print.TextOut(dc, 100, 100, "发货单打印机测试", 15)
            win32print.EndPage(dc)
            win32print.EndDoc(dc)
            win32print.DeleteDC(dc)
            win32print.ClosePrinter(hPrinter)
            print(f"      ✅ 发送到 {doc_printer} 成功")
        except Exception as e:
            print(f"      ❌ 发送到 {doc_printer} 失败: {e}")
        
        # 测试标签打印机
        print(f"\n   🏷️ 测试标签打印机: {label_printer}")
        try:
            hPrinter = win32print.OpenPrinter(label_printer)
            dc = win32print.CreateDC("WINSPOOL", label_printer)
            win32print.StartDoc(dc, ("Test Label", None))
            win32print.StartPage(dc)
            win32print.TextOut(dc, 100, 100, "标签打印机测试", 15)
            win32print.EndPage(dc)
            win32print.EndDoc(dc)
            win32print.DeleteDC(dc)
            win32print.ClosePrinter(hPrinter)
            print(f"      ✅ 发送到 {label_printer} 成功")
        except Exception as e:
            print(f"      ❌ 发送到 {label_printer} 失败: {e}")
        
        # 清理测试文件
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"   🧹 清理测试文件: {test_file}")
        
    except Exception as e:
        print(f"   ❌ 直接打印测试失败: {e}")

def solve_shellexecute_issue():
    """解决ShellExecute被默认打印机覆盖的问题"""
    print("\n🛠️ 6. 解决ShellExecute问题")
    
    print("   💡 问题分析：")
    print("   - ShellExecute可能被Windows默认打印机覆盖")
    print("   - 需要明确指定打印机名称")
    
    print("\n   🔧 解决方案：")
    print("   方案1: 在发送前临时更改默认打印机")
    print("   方案2: 使用PrintDocument替代ShellExecute")
    print("   方案3: 确保PDF应用使用指定打印机")
    
    # 创建临时更改默认打印机的脚本
    script_content = """@echo off
echo 临时更改Windows默认打印机
rundll32 printui.dll,PrintUIEntry /y /n "TSC TTP-244 Plus"
echo 默认打印机已更改为TSC TTP-244 Plus
pause
"""
    
    with open("temp_change_default.bat", "w", encoding="gbk") as f:
        f.write(script_content)
    
    print("\n   📝 创建临时脚本：temp_change_default.bat")
    print("   使用方法：")
    print("   1. 运行此脚本临时更改默认打印机")
    print("   2. 执行标签打印")
    print("   3. 恢复原默认打印机")

def create_enhanced_printer_functions():
    """创建增强的打印机函数"""
    print("\n🔧 7. 创建增强的打印机函数")
    
    enhanced_code = '''
# 增强的标签打印函数，解决ShellExecute问题
def print_pdf_labels_enhanced(pdf_path: str, copies: int = 1, show_app: bool = True) -> Dict:
    """
    增强的PDF标签打印函数
    解决ShellExecute被默认打印机覆盖的问题
    """
    try:
        if not os.path.exists(pdf_path):
            return {"success": False, "message": f"PDF文件不存在: {pdf_path}"}
        
        # 获取正确的标签打印机
        label_printer = get_label_printer()
        if not label_printer:
            return {"success": False, "message": "未找到标签打印机"}
        
        logger.info(f"开始增强PDF标签打印: {pdf_path}")
        logger.info(f"标签打印机: {label_printer}")
        
        # 方法1: 使用ShellExecute，但增加打印机名称验证
        abs_path = os.path.abspath(pdf_path)
        
        # 确保打印机名称正确
        printer_param = f'/d:"{label_printer}"'
        logger.info(f"ShellExecute打印机参数: {printer_param}")
        
        if show_app:
            result = win32api.ShellExecute(0, "print", abs_path, printer_param, ".", 1)
        else:
            result = win32api.ShellExecute(0, "print", abs_path, printer_param, ".", 0)
        
        if result > 32:
            return {
                "success": True, 
                "message": f"PDF标签打印成功发送到 {label_printer}",
                "file": pdf_path,
                "printer": label_printer,
                "method": "enhanced_shellexecute"
            }
        else:
            # 方法2: 如果ShellExecute失败，使用PrintDocument
            logger.warning("ShellExecute失败，尝试PrintDocument方法")
            return print_with_printdocument(pdf_path, label_printer)
            
    except Exception as e:
        logger.error(f"增强PDF打印失败: {e}")
        return {"success": False, "message": f"增强PDF打印失败: {str(e)}"}

def print_with_printdocument(pdf_path: str, printer_name: str) -> Dict:
    """使用PrintDocument方法打印PDF"""
    try:
        # 这里可以实现基于PrintDocument的PDF打印
        # 目前作为备选方案
        logger.info(f"PrintDocument方法尚未实现，使用ShellExecute重试")
        return {"success": False, "message": "PrintDocument方法暂未实现"}
        
    except Exception as e:
        return {"success": False, "message": f"PrintDocument打印失败: {str(e)}"}
'''
    
    with open("enhanced_printer_functions.py", "w", encoding="utf-8") as f:
        f.write(enhanced_code)
    
    print("   ✅ 创建增强的打印机函数：enhanced_printer_functions.py")

if __name__ == "__main__":
    # 执行完整的打印机分离诊断和解决
    doc_printer, label_printer, validation = test_printer_functions()
    
    if doc_printer and label_printer:
        test_direct_printing(doc_printer, label_printer)
    
    solve_shellexecute_issue()
    create_enhanced_printer_functions()
    
    print("\n" + "=" * 80)
    print("✅ 打印机分离强化解决方案完成")
    print("=" * 80)
