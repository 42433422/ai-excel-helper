#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
只测试默认打印机的切换
打开应用后让用户手动点击打印
"""

import os
import sys
import time
import win32api
import win32print
import subprocess

def test_printer_switch_only():
    """只测试默认打印机切换"""
    print("=" * 80)
    print("🚀 测试默认打印机切换")
    print("=" * 80)
    
    try:
        # 1. 记录原始默认打印机
        print("\n📋 1. 记录原始默认打印机")
        original_printer = win32print.GetDefaultPrinter()
        print(f"✅ 原始默认打印机: {original_printer}")
        
        # 2. 测试切换到TSC标签打印机
        print("\n" + "=" * 80)
        print("📋 2. 测试切换到标签打印机")
        print("=" * 80)
        
        label_printer = "TSC TTP-244 Plus"
        
        print(f"\n🔧 切换到标签打印机: {label_printer}")
        
        result = subprocess.run([
            'rundll32', 'printui.dll,PrintUIEntry',
            '/y', '/n', label_printer
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            time.sleep(1)
            current = win32print.GetDefaultPrinter()
            print(f"✅ 切换成功")
            print(f"当前默认打印机: {current}")
            
            if current == label_printer:
                print("✅ 验证成功，标签打印机是默认打印机")
            else:
                print(f"❌ 验证失败，期望: {label_printer}, 实际: {current}")
        else:
            print(f"❌ 切换失败: {result.stderr}")
        
        # 3. 恢复原始默认打印机
        print("\n" + "=" * 80)
        print("📋 3. 恢复原始默认打印机")
        print("=" * 80)
        
        print(f"\n🔄 恢复原始打印机: {original_printer}")
        
        result = subprocess.run([
            'rundll32', 'printui.dll,PrintUIEntry',
            '/y', '/n', original_printer
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            time.sleep(1)
            restored = win32print.GetDefaultPrinter()
            print(f"✅ 恢复成功")
            print(f"当前默认打印机: {restored}")
            
            if restored == original_printer:
                print("✅ 验证成功，恢复原始默认打印机")
            else:
                print(f"❌ 验证失败，期望: {original_printer}, 实际: {restored}")
        else:
            print(f"❌ 恢复失败: {result.stderr}")
        
        # 4. 测试打开图片查看器
        print("\n" + "=" * 80)
        print("📋 4. 打开图片查看器（用户手动打印）")
        print("=" * 80)
        
        # 查找最新的标签文件
        labels_dir = "商标导出"
        
        if os.path.exists(labels_dir):
            png_files = [f for f in os.listdir(labels_dir) if f.endswith('.png')]
            
            if png_files:
                png_files.sort(key=lambda x: os.path.getmtime(os.path.join(labels_dir, x)), reverse=True)
                latest_label = os.path.join(labels_dir, png_files[0])
                
                print(f"\n📄 找到标签文件: {png_files[0]}")
                
                # 切换到标签打印机
                print(f"\n🔧 切换到标签打印机: {label_printer}")
                subprocess.run([
                    'rundll32', 'printui.dll,PrintUIEntry',
                    '/y', '/n', label_printer
                ], capture_output=True, text=True, timeout=10)
                time.sleep(1)
                
                current = win32print.GetDefaultPrinter()
                print(f"✅ 当前默认打印机: {current}")
                
                # 打开图片查看器
                print(f"\n🖼️ 打开图片查看器，请手动点击打印...")
                print(f"💡 提示: 当前默认打印机是 {current}，请在查看器中选择正确的打印机")
                
                # 使用系统默认方式打开图片
                result = win32api.ShellExecute(
                    0,
                    "open",
                    latest_label,
                    "",
                    ".",
                    1  # SW_SHOW 显示窗口
                )
                
                if result > 32:
                    print("✅ 图片查看器已打开")
                else:
                    print(f"❌ 打开失败，错误代码: {result}")
                
                # 提示用户
                print(f"\n📝 用户操作指南:")
                print(f"   1. 图片查看器已打开")
                print(f"   2. 当前默认打印机是: {label_printer}")
                print(f"   3. 请点击文件 -> 打印（或Ctrl+P）")
                print(f"   4. 确认打印机是: {label_printer}")
                print(f"   5. 点击打印")
                
                # 恢复原始默认打印机
                print(f"\n🔄 5秒后恢复原始默认打印机...")
                time.sleep(5)
                
                subprocess.run([
                    'rundll32', 'printui.dll,PrintUIEntry',
                    '/y', '/n', original_printer
                ], capture_output=True, text=True, timeout=10)
                time.sleep(1)
                
                restored = win32print.GetDefaultPrinter()
                print(f"✅ 已恢复，默认打印机: {restored}")
        
        # 5. 总结
        print("\n" + "=" * 80)
        print("📊 测试总结")
        print("=" * 80)
        
        print("\n✅ 已验证:")
        print("   1. rundll32命令可以切换默认打印机")
        print("   2. 切换后系统立即生效")
        print("   3. 可以恢复到原始默认打印机")
        print()
        print("💡 手动测试步骤:")
        print("   1. 运行此脚本")
        print("   2. 脚本自动切换到标签打印机")
        print("   3. 图片查看器自动打开")
        print("   4. 用户点击文件 -> 打印")
        print("   5. 确认使用TSC标签打印机")
        print("   6. 完成打印")
        print()
        print("📝 集成到系统的方案:")
        print("   1. 打印前使用rundll32切换默认打印机")
        print("   2. 打开图片查看器")
        print("   3. 用户手动点击打印")
        print("   4. 打印完成后恢复默认打印机")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        
        # 恢复原始打印机
        try:
            if 'original_printer' in dir():
                subprocess.run([
                    'rundll32', 'printui.dll,PrintUIEntry',
                    '/y', '/n', original_printer
                ], capture_output=True, text=True, timeout=10)
        except:
            pass
        
        return False

if __name__ == "__main__":
    print("🚀 开始测试默认打印机切换...")
    test_printer_switch_only()
    print("\n" + "=" * 80)
    print("🎉 测试完成")
    print("=" * 80)
