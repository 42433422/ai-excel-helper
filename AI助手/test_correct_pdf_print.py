#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试正确的打印机切换方案
关键：在打印PDF前先切换默认打印机，确保PDF应用使用正确的打印机
"""

import os
import sys
import time
import win32api
import win32print
import subprocess

def test_printer_switch_for_pdf():
    """测试打印机切换方案（针对PDF应用）"""
    print("=" * 80)
    print("🚀 测试打印机切换方案（针对PDF应用）")
    print("=" * 80)
    
    try:
        # 1. 记录原始默认打印机
        print("\n📋 1. 记录原始默认打印机")
        original_printer = win32print.GetDefaultPrinter()
        print(f"✅ 原始默认打印机: {original_printer}")
        
        # 2. 查找最新的标签PDF
        print("\n📋 2. 查找最新的标签PDF")
        labels_dir = "商标导出"
        
        if not os.path.exists(labels_dir):
            print(f"❌ 目录不存在: {labels_dir}")
            return False
        
        # 查找PNG标签文件（因为标签是PNG格式）
        png_files = [f for f in os.listdir(labels_dir) if f.endswith('.png')]
        
        if not png_files:
            print("❌ 没有找到标签PNG文件")
            return False
        
        # 按修改时间排序
        png_files.sort(key=lambda x: os.path.getmtime(os.path.join(labels_dir, x)), reverse=True)
        latest_label = png_files[0]
        label_path = os.path.join(labels_dir, latest_label)
        
        print(f"✅ 找到最新标签: {latest_label}")
        
        # 3. 查找PDF阅读器
        print("\n📋 3. 查找PDF阅读器")
        
        pdf_readers = [
            r"C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
            r"C:\Program Files\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
            r"C:\Program Files (x86)\Foxit Software\Foxit Reader\FoxitReader.exe",
            r"C:\Program Files\Foxit Software\Foxit Reader\FoxitReader.exe",
        ]
        
        pdf_reader = None
        for reader in pdf_readers:
            if os.path.exists(reader):
                pdf_reader = reader
                print(f"✅ 找到PDF阅读器: {reader}")
                break
        
        if not pdf_reader:
            print("❌ 未找到PDF阅读器")
            print("💡 提示: 请安装Adobe Acrobat Reader或Foxit Reader")
            return False
        
        # 4. 测试标签打印流程
        print("\n" + "=" * 80)
        print("📋 4. 测试标签打印流程")
        print("=" * 80)
        
        label_printer = "TSC TTP-244 Plus"
        doc_printer = "Jolimark 24-pin printer"
        
        print(f"\n📄 标签打印测试:")
        print(f"目标打印机: {label_printer}")
        print(f"PDF阅读器: {pdf_reader}")
        
        # 步骤1：切换到标签打印机
        print(f"\n🔧 步骤1: 切换默认打印机到 {label_printer}")
        
        result = subprocess.run([
            'rundll32', 'printui.dll,PrintUIEntry',
            '/y', '/n', label_printer
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"❌ 切换失败: {result.stderr}")
            return False
        
        time.sleep(1)  # 等待系统更新
        
        # 验证切换结果
        current_default = win32print.GetDefaultPrinter()
        print(f"当前默认打印机: {current_default}")
        
        if current_default != label_printer:
            print(f"❌ 切换验证失败，期望: {label_printer}, 实际: {current_default}")
            # 恢复原始打印机
            subprocess.run([
                'rundll32', 'printui.dll,PrintUIEntry',
                '/y', '/n', original_printer
            ], capture_output=True, text=True, timeout=10)
            return False
        
        print("✅ 切换成功")
        
        # 步骤2：执行打印（打开PDF应用）
        print(f"\n🖨️ 步骤2: 执行打印（打开PDF应用）")
        
        # 使用Adobe Reader的命令行参数打印
        # /t = 打印任务，参数: 文件名 打印机名 用户名 密码
        print_pdf_cmd = [
            pdf_reader,
            "/t",
            label_path,
            label_printer
        ]
        
        print(f"执行命令: {' '.join(print_pdf_cmd)}")
        
        result = subprocess.run(
            print_pdf_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"返回码: {result.returncode}")
        print(f"stdout: {result.stdout[:200] if result.stdout else '无'}")
        print(f"stderr: {result.stderr[:200] if result.stderr else '无'}")
        
        if result.returncode == 0:
            print("✅ 打印命令执行成功")
        else:
            print(f"⚠️ 打印命令返回非零状态: {result.returncode}")
            print("💡 这可能是因为PDF应用打开后需要用户确认打印")
        
        # 步骤3：恢复原始默认打印机
        print(f"\n🔄 步骤3: 恢复原始默认打印机")
        
        result = subprocess.run([
            'rundll32', 'printui.dll,PrintUIEntry',
            '/y', '/n', original_printer
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            time.sleep(1)
            restored = win32print.GetDefaultPrinter()
            print(f"恢复后默认打印机: {restored}")
            
            if restored == original_printer:
                print("✅ 成功恢复原始默认打印机")
            else:
                print(f"⚠️ 恢复验证失败")
        else:
            print(f"❌ 恢复失败: {result.stderr}")
        
        # 5. 检查打印机队列
        print("\n" + "=" * 80)
        print("📋 5. 检查打印机队列")
        print("=" * 80)
        
        time.sleep(2)  # 等待任务进入队列
        
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
                
                # 检查文档名是否包含"标签"
                has_label_task = any("标签" in str(job.get('pDocument', '')) for job in jobs)
                if has_label_task:
                    print("   ✅ 标签任务在正确的打印机上")
                else:
                    print("   ⚠️ 标签任务可能不在此打印机上")
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
        print("   1. 使用PDF阅读器的命令行参数打印")
        print("   2. 在打印前切换默认打印机")
        print("   3. 使用 /t 参数进行静默打印")
        print()
        print("📝 命令格式:")
        print("   AdobeReader.exe /t filename printername")
        print()
        print("⚠️ 注意事项:")
        print("   - 确保PDF阅读器已安装")
        print("   - 切换默认打印机后等待1秒")
        print("   - 打印完成后立即恢复默认打印机")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        
        # 确保恢复原始打印机
        try:
            if 'original_printer' in dir():
                subprocess.run([
                    'rundll32', 'printui.dll,PrintUIEntry',
                    '/y', '/n', original_printer
                ], capture_output=True, text=True, timeout=10)
                print("已恢复原始默认打印机")
        except:
            pass
        
        return False

if __name__ == "__main__":
    print("🚀 开始测试打印机切换方案...")
    test_printer_switch_for_pdf()
    print("\n" + "=" * 80)
    print("🎉 测试完成")
    print("=" * 80)
