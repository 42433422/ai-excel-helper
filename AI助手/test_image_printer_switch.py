#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试打印机切换方案（针对PNG标签，因为标签实际上是PNG格式）
关键：在打印前切换默认打印机，确保图片查看器使用正确的打印机
"""

import os
import sys
import time
import win32api
import win32print
import subprocess
import ctypes

def get_default_printer():
    """获取Windows默认打印机"""
    try:
        return win32print.GetDefaultPrinter()
    except:
        return None

def switch_default_printer(target_printer):
    """切换默认打印机"""
    try:
        result = subprocess.run([
            'rundll32', 'printui.dll,PrintUIEntry',
            '/y', '/n', target_printer
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            time.sleep(1)  # 等待系统更新
            return True
        return False
    except Exception as e:
        print(f"切换打印机失败: {e}")
        return False

def test_printer_switch_for_image():
    """测试打印机切换方案（针对PNG图片）"""
    print("=" * 80)
    print("🚀 测试打印机切换方案（针对PNG图片标签）")
    print("=" * 80)
    
    try:
        # 1. 记录原始默认打印机
        print("\n📋 1. 记录原始默认打印机")
        original_printer = get_default_printer()
        print(f"✅ 原始默认打印机: {original_printer}")
        
        # 2. 查找最新的标签PNG
        print("\n📋 2. 查找最新的标签PNG")
        labels_dir = "商标导出"
        
        if not os.path.exists(labels_dir):
            print(f"❌ 目录不存在: {labels_dir}")
            return False
        
        png_files = [f for f in os.listdir(labels_dir) if f.endswith('.png')]
        
        if not png_files:
            print("❌ 没有找到标签PNG文件")
            return False
        
        # 按修改时间排序
        png_files.sort(key=lambda x: os.path.getmtime(os.path.join(labels_dir, x)), reverse=True)
        latest_label = png_files[0]
        label_path = os.path.join(labels_dir, latest_label)
        
        print(f"✅ 找到最新标签: {latest_label}")
        print(f"   路径: {label_path}")
        
        # 3. 获取系统默认的PNG处理程序
        print("\n📋 3. 获取PNG文件的默认打开方式")
        
        try:
            # 使用assoc查询文件关联
            result = subprocess.run(['assoc', '.png'], capture_output=True, text=True)
            if result.returncode == 0:
                png_association = result.stdout.strip()
                print(f"   PNG关联: {png_association}")
                
                # 获取对应的程序
                if '=' in png_association:
                    prog_id = png_association.split('=')[1]
                    result2 = subprocess.run(['ftype', prog_id], capture_output=True, text=True)
                    if result2.returncode == 0:
                        png_program = result2.stdout.strip()
                        print(f"   打开程序: {png_program}")
        except Exception as e:
            print(f"   ⚠️ 获取PNG关联失败: {e}")
        
        # 4. 测试标签打印流程
        print("\n" + "=" * 80)
        print("📋 4. 测试标签打印流程")
        print("=" * 80)
        
        label_printer = "TSC TTP-244 Plus"
        doc_printer = "Jolimark 24-pin printer"
        
        print(f"\n🎯 目标打印机: {label_printer}")
        print(f"📄 当前默认打印机: {original_printer}")
        
        # 步骤1：切换到标签打印机
        print(f"\n🔧 步骤1: 切换默认打印机到 {label_printer}")
        
        if switch_default_printer(label_printer):
            current = get_default_printer()
            print(f"✅ 切换成功，当前默认: {current}")
            
            if current == label_printer:
                print("✅ 验证成功")
            else:
                print(f"❌ 验证失败，期望: {label_printer}, 实际: {current}")
        else:
            print("❌ 切换失败")
        
        # 步骤2：使用rundll32打印图片
        print(f"\n🖨️ 步骤2: 使用rundll32打印图片")
        
        # 使用rund32 printui打印图片
        print_cmd = [
            'rundll32',
            'printui.dll,PrintUIEntry',
            '/p',
            '/f', label_path,
            '/d', label_printer
        ]
        
        print(f"执行命令: {' '.join(print_cmd)}")
        
        result = subprocess.run(
            print_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"返回码: {result.returncode}")
        print(f"stdout: {result.stdout[:200] if result.stdout else '无'}")
        print(f"stderr: {result.stderr[:200] if result.stderr else '无'}")
        
        # 步骤3：恢复原始默认打印机
        print(f"\n🔄 步骤3: 恢复原始默认打印机")
        
        if switch_default_printer(original_printer):
            restored = get_default_printer()
            print(f"✅ 恢复成功，当前默认: {restored}")
        else:
            print("❌ 恢复失败")
        
        # 5. 检查打印机队列
        print("\n" + "=" * 80)
        print("📋 5. 检查打印机队列")
        print("=" * 80)
        
        time.sleep(2)
        
        # 检查标签打印机
        try:
            hPrinter = win32print.OpenPrinter(label_printer)
            jobs = win32print.EnumJobs(hPrinter, 0, -1, 1)
            win32print.ClosePrinter(hPrinter)
            
            print(f"\n🏷️ 标签打印机 ({label_printer}):")
            if jobs:
                print(f"   有 {len(jobs)} 个任务:")
                for job in jobs:
                    print(f"     - 作业ID: {job['JobId']}, 文档: {job.get('pDocument', 'Unknown')}")
            else:
                print("   队列为空")
        except Exception as e:
            print(f"   ❌ 检查失败: {e}")
        
        # 检查发货单打印机
        try:
            hPrinter = win32print.OpenPrinter(doc_printer)
            jobs = win32print.EnumJobs(hPrinter, 0, -1, 1)
            win32print.ClosePrinter(hPrinter)
            
            print(f"\n📄 发货单打印机 ({doc_printer}):")
            if jobs:
                print(f"   有 {len(jobs)} 个任务:")
                for job in jobs:
                    print(f"     - 作业ID: {job['JobId']}, 文档: {job.get('pDocument', 'Unknown')}")
            else:
                print("   队列为空")
        except Exception as e:
            print(f"   ❌ 检查失败: {e}")
        
        # 6. 总结
        print("\n" + "=" * 80)
        print("📊 测试总结")
        print("=" * 80)
        
        print("\n💡 推荐方案:")
        print("   1. 使用rundll32 printui打印PNG图片")
        print("   2. 命令: rundll32 printui.dll,PrintUIEntry /p /f 文件路径 /d 打印机")
        print()
        print("📝 打印流程:")
        print("   1. 切换默认打印机到目标打印机")
        print("   2. 使用rundll32 printui打印文件")
        print("   3. 恢复原始默认打印机")
        print()
        print("⚠️ 注意:")
        print("   - 标签是PNG格式，不是PDF")
        print("   - 使用图片查看器或rundll32 printui打印")
        print("   - 确保打印机名称正确")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        
        # 恢复原始打印机
        try:
            if original_printer:
                switch_default_printer(original_printer)
        except:
            pass
        
        return False

def test_with_shellexecute():
    """使用ShellExecute测试（简化版）"""
    print("\n" + "=" * 80)
    print("📋 使用ShellExecute测试（简化版）")
    print("=" * 80)
    
    try:
        original_printer = get_default_printer()
        label_printer = "TSC TTP-244 Plus"
        
        print(f"\n🔧 切换到标签打印机")
        if switch_default_printer(label_printer):
            print(f"✅ 切换成功")
        
        # 使用ShellExecute "print" 打印
        print(f"\n🖨️ 使用ShellExecute打印")
        
        result = win32api.ShellExecute(
            0,
            "print",
            label_path,
            f'/d:"{label_printer}"',
            ".",
            1  # SW_SHOW 显示窗口
        )
        
        print(f"ShellExecute结果: {result}")
        
        if result > 32:
            print("✅ ShellExecute调用成功")
        else:
            print(f"❌ ShellExecute失败，错误代码: {result}")
        
        # 恢复
        print(f"\n🔄 恢复原始打印机")
        switch_default_printer(original_printer)
        
        return True
        
    except Exception as e:
        print(f"测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始测试打印机切换方案...")
    
    # 运行测试
    test_success = test_printer_switch_for_image()
    
    print("\n" + "=" * 80)
    print("🎉 测试完成")
    print("=" * 80)
