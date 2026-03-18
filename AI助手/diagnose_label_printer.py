#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
紧急修复标签打印机的分配问题
问题：标签被发送到发货单打印机而不是标签打印机
"""

import os
import sys
import json
import time
import requests

def diagnose_label_printer_issue():
    """诊断标签打印机分配问题"""
    print("=" * 80)
    print("🚨 标签打印机分配问题诊断")
    print("=" * 80)
    
    try:
        # 1. 检查后端返回的打印机信息
        print("\n📋 1. 检查后端返回的打印机信息")
        
        # 获取打印机列表
        response = requests.get("http://127.0.0.1:5000/api/printers", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 后端返回的打印机列表:")
            print(json.dumps(data, ensure_ascii=False, indent=2))
        
        # 2. 发送测试订单
        print("\n📋 2. 发送测试订单并详细记录")
        
        order_text = "七彩乐园一桶PE白底漆规格28"
        
        test_order = {
            "order_text": order_text,
            "template_name": "尹玉华1.xlsx",
            "custom_mode": False,
            "number_mode": False,
            "excel_sync": False,
            "auto_print": True
        }
        
        print(f"订单: {order_text}")
        
        response = requests.post(
            "http://127.0.0.1:5000/api/generate",
            json=test_order,
            timeout=90
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                print(f"✅ 订单生成成功")
                
                # 重点：检查生成的文件
                if 'document' in result:
                    doc = result['document']
                    print(f"\n📄 发货单文件:")
                    print(f"   路径: {doc.get('output_path', '未知')}")
                
                if 'labels' in result:
                    labels = result['labels']
                    print(f"\n🏷️ 标签文件:")
                    for label in labels:
                        print(f"   路径: {label.get('file_path', '未知')}")
                
                # 重点：检查打印结果中的打印机信息
                if 'printing' in result:
                    printing = result['printing']
                    print(f"\n🖨️ 打印结果详情:")
                    print(f"   document_result: {json.dumps(printing.get('document_result', {}), ensure_ascii=False)}")
                    print(f"   labels_result: {json.dumps(printing.get('labels_result', {}), ensure_ascii=False)}")
        
        # 3. 重点检查：标签打印时使用的打印机
        print("\n" + "=" * 80)
        print("🔍 重点：检查标签打印时的打印机分配")
        print("=" * 80)
        
        # 检查生成的最后几个标签PDF
        labels_dir = "商标导出"
        if os.path.exists(labels_dir):
            files = sorted(os.listdir(labels_dir), key=lambda x: os.path.getmtime(os.path.join(labels_dir, x)), reverse=True)
            print(f"\n📁 标签导出目录 ({labels_dir}):")
            print(f"找到 {len(files)} 个文件:")
            
            for i, f in enumerate(files[:5]):  # 只显示最近5个
                filepath = os.path.join(labels_dir, f)
                mtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(filepath)))
                print(f"   {i+1}. {f} ({mtime})")
            
            # 查找标签PDF文件
            pdf_files = [f for f in files if f.endswith('.pdf')]
            print(f"\n📑 标签PDF文件:")
            for pdf in pdf_files[:3]:
                filepath = os.path.join(labels_dir, pdf)
                size = os.path.getsize(filepath)
                print(f"   - {pdf} ({size} bytes)")
        
        # 4. 模拟标签打印流程
        print("\n" + "=" * 80)
        print("🧪 模拟标签打印流程")
        print("=" * 80)
        
        # 查找最新的标签PDF
        labels_dir = "商标导出"
        pdf_file = None
        
        if os.path.exists(labels_dir):
            files = [f for f in os.listdir(labels_dir) if f.endswith('.pdf')]
            if files:
                # 按修改时间排序
                files.sort(key=lambda x: os.path.getmtime(os.path.join(labels_dir, x)), reverse=True)
                pdf_file = os.path.join(labels_dir, files[0])
                print(f"找到最新的标签PDF: {pdf_file}")
        
        if pdf_file and os.path.exists(pdf_file):
            # 测试直接使用标签打印机打印
            label_printer = "TSC TTP-244 Plus"
            print(f"\n🎯 尝试直接打印到标签打印机:")
            print(f"   文件: {pdf_file}")
            print(f"   打印机: {label_printer}")
            
            # 使用我们的自动化模块
            import win32api
            import win32print
            
            # 先检查打印机状态
            try:
                hPrinter = win32print.OpenPrinter(label_printer)
                printer_info = win32print.GetPrinter(hPrinter, 2)
                print(f"   打印机状态: {printer_info.get('Status', '未知')}")
                win32print.ClosePrinter(hPrinter)
            except Exception as e:
                print(f"   ❌ 检查打印机状态失败: {e}")
            
            # 尝试打印
            result = win32api.ShellExecute(
                0,
                "print",
                pdf_file,
                f'/d:"{label_printer}"',
                ".",
                1  # SW_SHOW
            )
            
            print(f"   ShellExecute结果: {result}")
            
            if result > 32:
                print(f"   ✅ 打印命令已发送")
            else:
                print(f"   ❌ 打印失败，错误代码: {result}")
        
        # 5. 总结和建议
        print("\n" + "=" * 80)
        print("📊 问题总结")
        print("=" * 80)
        
        print("\n❌ 问题确认:")
        print("   标签被发送到发货单打印机而不是标签打印机")
        print("   原因可能是:")
        print("   1. PDF应用默认打印机设置错误")
        print("   2. ShellExecute参数格式问题")
        print("   3. 临时更改默认打印机失败")
        print("   4. 打印机分配逻辑有误")
        
        print("\n💡 建议的修复方案:")
        print("   1. 在打印标签前，临时将TSC设为默认打印机")
        print("   2. 使用正确的ShellExecute参数格式")
        print("   3. 打印完成后恢复原来的默认打印机")
        print("   4. 添加更详细的日志记录")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 诊断过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始标签打印机分配问题诊断...")
    diagnose_label_printer_issue()
    print("\n" + "=" * 80)
    print("🎉 诊断完成")
    print("=" * 80)
