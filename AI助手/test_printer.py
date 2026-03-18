#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试打印机功能
"""

import win32print
import win32api
import os
import time

# 测试打印机名称
PRINTER_NAME = "Jolimark 24-pin printer"
TEST_FILE = r"C:\Users\Administrator\Desktop\新建文件夹 (4)\AI助手\outputs\发货单_26-0200092A_20260209_210940.xlsx"

def test_printer_status():
    """测试打印机状态"""
    print(f"\n=== 测试打印机状态: {PRINTER_NAME} ===")
    
    try:
        # 获取打印机句柄
        handle = win32print.OpenPrinter(PRINTER_NAME)
        info = win32print.GetPrinter(handle, 2)
        win32print.ClosePrinter(handle)
        
        status = info['Status']
        attributes = info['Attributes']
        
        print(f"状态码: {status}")
        print(f"属性码: {attributes}")
        
        # 状态码解释
        if status == 0:
            print("✅ 打印机状态: 就绪")
        elif status & 0x00000001:
            print("⚠️ 打印机状态: 暂停")
        elif status & 0x00000002:
            print("⚠️ 打印机状态: 错误")
        elif status & 0x00000010:
            print("⚠️ 打印机状态: 脱机")
        elif status & 0x00000020:
            print("⚠️ 打印机状态: 缺纸")
        else:
            print(f"⚠️ 打印机状态: 未知状态码 {status}")
            
        # 检查是否脱机
        if attributes & 0x00000400:
            print("⚠️ 注意: 打印机设置为脱机工作")
            
        return status == 0
        
    except Exception as e:
        print(f"❌ 获取打印机状态失败: {e}")
        return False

def test_default_printer():
    """测试默认打印机"""
    print("\n=== 测试默认打印机 ===")
    
    try:
        default = win32print.GetDefaultPrinter()
        print(f"当前默认打印机: {default}")
        
        if default != PRINTER_NAME:
            print(f"正在修改默认打印机为: {PRINTER_NAME}")
            win32print.SetDefaultPrinter(PRINTER_NAME)
            time.sleep(1)
            new_default = win32print.GetDefaultPrinter()
            print(f"修改后默认打印机: {new_default}")
            
            if new_default == PRINTER_NAME:
                print("✅ 默认打印机修改成功")
                return True
            else:
                print("❌ 默认打印机修改失败")
                return False
        else:
            print("✅ 默认打印机已经是目标打印机")
            return True
            
    except Exception as e:
        print(f"❌ 修改默认打印机失败: {e}")
        return False

def test_print_file():
    """测试打印文件"""
    print(f"\n=== 测试打印文件 ===")
    
    if not os.path.exists(TEST_FILE):
        print(f"❌ 测试文件不存在: {TEST_FILE}")
        return False
    
    print(f"测试文件: {TEST_FILE}")
    
    # 方法1: ShellExecute
    print("\n方法1: 使用 ShellExecute")
    try:
        result = win32api.ShellExecute(
            0,
            "print",
            TEST_FILE,
            None,
            ".",
            1
        )
        print(f"ShellExecute 结果: {result}")
        if result > 32:
            print("✅ ShellExecute 打印命令已发送")
            return True
        else:
            print(f"❌ ShellExecute 失败，错误代码: {result}")
    except Exception as e:
        print(f"❌ ShellExecute 失败: {e}")
    
    # 方法2: os.startfile
    print("\n方法2: 使用 os.startfile")
    try:
        os.startfile(TEST_FILE, "print")
        print("✅ os.startfile 打印命令已发送")
        return True
    except Exception as e:
        print(f"❌ os.startfile 失败: {e}")
    
    # 方法3: 直接打开文件
    print("\n方法3: 直接打开文件")
    try:
        os.startfile(TEST_FILE)
        print("✅ 文件已打开，请手动打印")
        return True
    except Exception as e:
        print(f"❌ 打开文件失败: {e}")
    
    return False

def restore_default_printer(original_printer):
    """恢复默认打印机"""
    print(f"\n=== 恢复默认打印机 ===")
    try:
        win32print.SetDefaultPrinter(original_printer)
        time.sleep(0.5)
        current = win32print.GetDefaultPrinter()
        print(f"默认打印机已恢复为: {current}")
    except Exception as e:
        print(f"❌ 恢复默认打印机失败: {e}")

def main():
    print("=" * 60)
    print("打印机测试程序")
    print("=" * 60)
    
    # 保存原始默认打印机
    original_printer = win32print.GetDefaultPrinter()
    print(f"原始默认打印机: {original_printer}")
    
    # 测试打印机状态
    status_ok = test_printer_status()
    
    # 测试修改默认打印机
    default_ok = test_default_printer()
    
    # 测试打印文件
    if status_ok and default_ok:
        print_ok = test_print_file()
    else:
        print("\n⚠️ 打印机状态或默认打印机设置有问题，跳过打印测试")
        print_ok = False
    
    # 恢复默认打印机
    restore_default_printer(original_printer)
    
    # 总结
    print("\n" + "=" * 60)
    print("测试结果总结:")
    print(f"  打印机状态: {'✅ 通过' if status_ok else '❌ 失败'}")
    print(f"  默认打印机: {'✅ 通过' if default_ok else '❌ 失败'}")
    print(f"  打印文件: {'✅ 通过' if print_ok else '❌ 失败'}")
    print("=" * 60)

if __name__ == "__main__":
    main()
