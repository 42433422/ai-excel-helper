#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试临时切换默认打印机的最佳方案
问题：ShellExecute的/d参数对PDF应用无效，必须直接切换Windows默认打印机
"""

import os
import sys
import time
import win32api
import win32print
import subprocess

def test_default_printer_switch():
    """测试临时切换默认打印机"""
    print("=" * 80)
    print("🚀 测试临时切换默认打印机")
    print("=" * 80)
    
    try:
        # 1. 记录原始默认打印机
        print("\n📋 1. 记录原始默认打印机")
        original_printer = win32print.GetDefaultPrinter()
        print(f"✅ 原始默认打印机: {original_printer}")
        
        # 2. 列出所有打印机
        print("\n📋 2. 列出所有可用打印机")
        printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)
        for i, printer in enumerate(printers):
            printer_name = printer[2]
            is_default = "✓ 默认" if printer_name == original_printer else ""
            print(f"   {i+1}. {printer_name} {is_default}")
        
        # 3. 测试方法1：使用rundll32切换默认打印机
        print("\n" + "=" * 80)
        print("📋 3. 测试方法1：使用rundll32切换默认打印机")
        print("=" * 80)
        
        target_printer = "TSC TTP-244 Plus"
        print(f"\n尝试将默认打印机设置为: {target_printer}")
        
        # 先保存原始打印机
        print(f"当前默认打印机: {win32print.GetDefaultPrinter()}")
        
        # 使用rundll32命令
        cmd = [
            'rundll32', 'printui.dll,PrintUIEntry',
            '/y', '/n', target_printer
        ]
        
        print(f"执行命令: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        print(f"返回码: {result.returncode}")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        
        # 检查是否切换成功
        time.sleep(1)  # 等待系统更新
        new_default = win32print.GetDefaultPrinter()
        print(f"\n切换后默认打印机: {new_default}")
        
        if new_default == target_printer:
            print(f"✅ 方法1成功！默认打印机已切换到 {target_printer}")
        else:
            print(f"❌ 方法1失败，默认打印机仍然是 {new_default}")
        
        # 4. 测试方法2：使用win32print.SetDefaultPrinter
        print("\n" + "=" * 80)
        print("📋 4. 测试方法2：使用win32print.SetDefaultPrinter")
        print("=" * 80)
        
        # 先恢复原始默认打印机
        subprocess.run([
            'rundll32', 'printui.dll,PrintUIEntry',
            '/y', '/n', original_printer
        ], capture_output=True, text=True, timeout=10)
        time.sleep(1)
        
        if win32print.GetDefaultPrinter() != original_printer:
            print(f"⚠️ 恢复原始打印机失败，当前: {win32print.GetDefaultPrinter()}")
        
        target_printer2 = "Jolimark 24-pin printer"
        print(f"\n尝试使用方法2将默认打印机设置为: {target_printer2}")
        
        # 检查win32print是否有SetDefaultPrinter函数
        if hasattr(win32print, 'SetDefaultPrinter'):
            try:
                win32print.SetDefaultPrinter(target_printer2)
                time.sleep(1)
                new_default2 = win32print.GetDefaultPrinter()
                print(f"切换后默认打印机: {new_default2}")
                
                if new_default2 == target_printer2:
                    print(f"✅ 方法2成功！")
                else:
                    print(f"❌ 方法2失败")
            except Exception as e:
                print(f"❌ 方法2异常: {e}")
        else:
            print("⚠️ win32print没有SetDefaultPrinter函数")
        
        # 5. 恢复原始默认打印机
        print("\n" + "=" * 80)
        print("📋 5. 恢复原始默认打印机")
        print("=" * 80)
        
        subprocess.run([
            'rundll32', 'printui.dll,PrintUIEntry',
            '/y', '/n', original_printer
        ], capture_output=True, text=True, timeout=10)
        time.sleep(1)
        
        restored = win32print.GetDefaultPrinter()
        print(f"恢复后默认打印机: {restored}")
        
        if restored == original_printer:
            print("✅ 成功恢复原始默认打印机")
        else:
            print(f"❌ 恢复失败，当前: {restored}")
        
        # 6. 总结
        print("\n" + "=" * 80)
        print("📊 测试总结")
        print("=" * 80)
        
        print("\n💡 推荐方案：")
        print("   使用rundll32命令切换默认打印机，这是最可靠的方法")
        print("   命令: rundll32 printui.dll,PrintUIEntry /y /n \"打印机名称\"")
        print()
        print("📝 切换流程：")
        print("   1. 保存当前默认打印机")
        print("   2. 使用rundll32命令切换到目标打印机")
        print("   3. 等待1秒让系统更新")
        print("   4. 执行打印任务")
        print("   5. 使用rundll32命令恢复原始打印机")
        print()
        print("⚠️ 注意事项：")
        print("   - ShellExecute的/d参数对某些PDF应用无效")
        print("   - 必须直接切换Windows默认打印机")
        print("   - 切换后等待1秒让系统生效")
        print("   - 打印完成后立即恢复默认打印机")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def implement_correct_printer_switch():
    """实现正确的打印机切换逻辑"""
    print("\n" + "=" * 80)
    print("🔧 实现正确的打印机切换逻辑")
    print("=" * 80)
    
    # 正确的打印机切换代码
    switch_code = '''
def switch_default_printer(target_printer):
    """
    临时切换默认打印机（使用rundll32命令）
    
    Args:
        target_printer: 目标打印机名称
    
    Returns:
        tuple: (原始打印机, 是否成功)
    """
    try:
        import win32print
        import subprocess
        import time
        
        # 1. 保存原始默认打印机
        original_printer = win32print.GetDefaultPrinter()
        print(f"原始默认打印机: {original_printer}")
        
        # 2. 切换到目标打印机
        if original_printer != target_printer:
            result = subprocess.run([
                'rundll32', 'printui.dll,PrintUIEntry',
                '/y', '/n', target_printer
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                print(f"切换打印机失败: {result.stderr}")
                return original_printer, False
            
            # 等待系统更新
            time.sleep(1)
            
            # 验证切换结果
            new_default = win32print.GetDefaultPrinter()
            if new_default != target_printer:
                print(f"切换验证失败: 期望 {target_printer}, 实际 {new_default}")
                return original_printer, False
            
            print(f"✅ 成功切换默认打印机到: {target_printer}")
        
        return original_printer, True
        
    except Exception as e:
        print(f"切换打印机异常: {e}")
        return None, False

def restore_default_printer(original_printer):
    """恢复原始默认打印机"""
    try:
        import win32print
        import subprocess
        import time
        
        if original_printer:
            result = subprocess.run([
                'rundll32', 'printui.dll,PrintUIEntry',
                '/y', '/n', original_printer
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                time.sleep(1)
                restored = win32print.GetDefaultPrinter()
                if restored == original_printer:
                    print(f"✅ 成功恢复默认打印机: {restored}")
                    return True
            
            print(f"❌ 恢复默认打印机失败")
            return False
        
    except Exception as e:
        print(f"恢复打印机异常: {e}")
        return False

# 使用示例
if __name__ == "__main__":
    import win32api
    
    # 标签打印
    label_printer = "TSC TTP-244 Plus"
    original, success = switch_default_printer(label_printer)
    
    if success:
        # 执行标签打印
        pdf_file = "标签.pdf"
        result = win32api.ShellExecute(
            0,
            "print",
            pdf_file,
            "",  # 不再需要/d参数
            ".",
            0  # 隐藏窗口
        )
        
        if result > 32:
            print("✅ 标签打印命令已发送")
        
        # 恢复原始默认打印机
        time.sleep(2)  # 等待打印完成
        restore_default_printer(original)
    
    # 发货单打印
    doc_printer = "Jolimark 24-pin printer"
    original, success = switch_default_printer(doc_printer)
    
    if success:
        # 执行发货单打印
        xlsx_file = "发货单.xlsx"
        result = win32api.ShellExecute(
            0,
            "print",
            xlsx_file,
            "",  # 不再需要/d参数
            ".",
            0  # 隐藏窗口
        )
        
        if result > 32:
            print("✅ 发货单打印命令已发送")
        
        # 恢复原始默认打印机
        time.sleep(2)  # 等待打印完成
        restore_default_printer(original)
'''
    
    print(switch_code)
    
    # 保存到文件
    with open('correct_printer_switch.py', 'w', encoding='utf-8') as f:
        f.write(switch_code)
    
    print("\n✅ 已保存正确的打印机切换代码到: correct_printer_switch.py")

if __name__ == "__main__":
    # 运行测试
    test_success = test_default_printer_switch()
    
    # 实现正确方案
    implement_correct_printer_switch()
    
    print("\n" + "=" * 80)
    print("🎉 测试完成")
    print("=" * 80)
