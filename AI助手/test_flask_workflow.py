#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试真正的Flask工作流程
"""

import sys
import os
import json

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_flask_workflow():
    """测试真正的Flask工作流程"""
    print("=" * 80)
    print("🧪 测试真正的Flask工作流程")
    print("=" * 80)
    
    try:
        import requests
        
        # 1. 检查Flask服务是否运行
        print("\n🌐 1. 检查Flask服务")
        try:
            response = requests.get("http://127.0.0.1:5000/api/printers")
            if response.status_code == 200:
                printers = response.json()
                print(f"   ✅ Flask服务正常运行")
                print(f"   📋 打印机列表: {printers}")
            else:
                print(f"   ❌ Flask服务异常: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ 无法连接Flask服务: {e}")
            return False
        
        # 2. 模拟一个简单的订单生成
        print("\n📋 2. 模拟订单生成")
        order_data = {
            "order_text": "订单测试 26-0200140A, 测试产品, 1个",
            "template_name": "尹玉华1.xlsx",
            "custom_mode": False,
            "number_mode": False,
            "excel_sync": False,
            "auto_print": True  # 启用自动打印
        }
        
        print(f"   订单数据: {order_data}")
        
        try:
            response = requests.post(
                "http://127.0.0.1:5000/api/generate",
                json=order_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ 订单生成成功")
                
                # 检查打印结果
                if 'printing' in result:
                    printing = result['printing']
                    print(f"   🖨️ 打印结果: {printing}")
                    
                    if printing.get('document_printed'):
                        print(f"   📄 发货单打印: 成功")
                    else:
                        print(f"   📄 发货单打印: {printing.get('document_result', '失败')}")
                    
                    if printing.get('labels_printed', 0) > 0:
                        print(f"   🏷️ 标签打印: 成功 ({printing.get('labels_printed')} 个)")
                    else:
                        print(f"   🏷️ 标签打印: {printing.get('labels_result', '失败')}")
                
                return True
            else:
                print(f"   ❌ 订单生成失败: {response.status_code}")
                print(f"   📄 响应内容: {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ 请求失败: {e}")
            return False
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_queue_after_test():
    """测试后检查队列"""
    print("\n📋 3. 检查测试后的打印机队列")
    
    try:
        import win32print
        
        # 检查TSC
        print("\n   TSC TTP-244 Plus:")
        try:
            hPrinter = win32print.OpenPrinter("TSC TTP-244 Plus")
            jobs = win32print.EnumJobs(hPrinter, 0, -1, 1)
            win32print.ClosePrinter(hPrinter)
            
            if jobs:
                print(f"   有 {len(jobs)} 个任务:")
                for job in jobs:
                    print(f"     - 作业ID: {job['JobId']}, 文档: {job.get('pDocument', 'Unknown')}")
            else:
                print("   队列为空")
        except Exception as e:
            print(f"   ❌ 检查TSC失败: {e}")
        
        # 检查Jolimark
        print("\n   Jolimark 24-pin printer:")
        try:
            hPrinter = win32print.OpenPrinter("Jolimark 24-pin printer")
            jobs = win32print.EnumJobs(hPrinter, 0, -1, 1)
            win32print.ClosePrinter(hPrinter)
            
            if jobs:
                print(f"   有 {len(jobs)} 个任务:")
                for job in jobs:
                    print(f"     - 作业ID: {job['JobId']}, 文档: {job.get('pDocument', 'Unknown')}")
            else:
                print("   队列为空")
        except Exception as e:
            print(f"   ❌ 检查Jolimark失败: {e}")
        
    except Exception as e:
        print(f"❌ 队列检查失败: {e}")

if __name__ == "__main__":
    print("🚀 开始测试Flask工作流程...")
    
    success = test_flask_workflow()
    
    if success:
        print("\n⏳ 等待3秒让打印任务进入队列...")
        import time
        time.sleep(3)
        check_queue_after_test()
    else:
        print("\n❌ Flask测试失败，无法继续检查队列")
    
    print("\n" + "=" * 80)
    print("📊 测试完成")
    print("=" * 80)
