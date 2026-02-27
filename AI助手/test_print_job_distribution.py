#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打印任务分配诊断脚本
检查打印任务是否正确发送到指定的打印机
"""

import os
import sys
import json
import time
import requests

def test_print_job_distribution():
    """测试打印任务分配"""
    print("=" * 80)
    print("🚀 打印任务分配测试")
    print("=" * 80)
    
    try:
        # 1. 检查Flask应用状态
        print("\n📋 1. 检查Flask应用状态")
        try:
            response = requests.get("http://127.0.0.1:5000/api/printers", timeout=5)
            if response.status_code == 200:
                printers = response.json()
                print(f"✅ Flask应用正常运行")
                print(f"📋 打印机列表:")
                for p in printers:
                    print(f"   - {p}")
            else:
                print(f"❌ Flask应用状态异常: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 无法连接Flask应用: {e}")
            return False
        
        # 2. 准备测试数据
        print("\n📋 2. 准备测试数据")
        test_order = {
            "order_text": "订单测试 26-0200200A: 测试产品A 1个 100元",
            "template_name": "尹玉华1.xlsx",
            "custom_mode": False,
            "number_mode": False,
            "excel_sync": False,
            "auto_print": True
        }
        
        print(f"测试订单文本: {test_order['order_text']}")
        print(f"自动打印: {test_order['auto_print']}")
        
        # 3. 发送测试请求并记录详细信息
        print("\n📋 3. 发送测试请求（记录详细日志）")
        print("⚠️ 注意观察打印任务是否正确分配到不同的打印机")
        
        try:
            response = requests.post(
                "http://127.0.0.1:5000/api/generate",
                json=test_order,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 订单生成成功")
                
                # 详细检查打印结果
                if 'printing' in result:
                    printing = result['printing']
                    print(f"\n📊 打印结果详情:")
                    print(f"  发货单打印: {printing.get('document_printed', False)}")
                    print(f"  标签打印: {printing.get('labels_printed', 0)}")
                    print(f"  发货单结果: {printing.get('document_result', '未知')}")
                    print(f"  标签结果: {printing.get('labels_result', '未知')}")
                else:
                    print(f"⚠️ 响应中没有打印结果")
                    print(f"完整响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                
                # 4. 检查打印机队列
                print("\n📋 4. 检查打印机队列")
                time.sleep(3)  # 等待任务进入队列
                
                import win32print
                
                # 检查发货单打印机
                try:
                    doc_printer = "Jolimark 24-pin printer"
                    hPrinter = win32print.OpenPrinter(doc_printer)
                    doc_jobs = win32print.EnumJobs(hPrinter, 0, -1, 1)
                    win32print.ClosePrinter(hPrinter)
                    
                    print(f"\n📄 发货单打印机 ({doc_printer}):")
                    if doc_jobs:
                        print(f"   有 {len(doc_jobs)} 个任务:")
                        for job in doc_jobs:
                            print(f"     - 作业ID: {job['JobId']}, 文档: {job.get('pDocument', 'Unknown')}")
                    else:
                        print(f"   队列为空")
                except Exception as e:
                    print(f"❌ 检查发货单打印机队列失败: {e}")
                
                # 检查标签打印机
                try:
                    label_printer = "TSC TTP-244 Plus"
                    hPrinter = win32print.OpenPrinter(label_printer)
                    label_jobs = win32print.EnumJobs(hPrinter, 0, -1, 1)
                    win32print.ClosePrinter(hPrinter)
                    
                    print(f"\n🏷️ 标签打印机 ({label_printer}):")
                    if label_jobs:
                        print(f"   有 {len(label_jobs)} 个任务:")
                        for job in label_jobs:
                            print(f"     - 作业ID: {job['JobId']}, 文档: {job.get('pDocument', 'Unknown')}")
                    else:
                        print(f"   队列为空")
                except Exception as e:
                    print(f"❌ 检查标签打印机队列失败: {e}")
                
                # 5. 分析问题
                print("\n" + "=" * 80)
                print("📊 问题分析")
                print("=" * 80)
                
                # 统计两个打印机的任务数量
                doc_job_count = len(doc_jobs) if 'doc_jobs' in dir() else 0
                label_job_count = len(label_jobs) if 'label_jobs' in dir() else 0
                
                print(f"\n📈 打印机任务统计:")
                print(f"  发货单打印机: {doc_job_count} 个任务")
                print(f"  标签打印机: {label_job_count} 个任务")
                print(f"  总计: {doc_job_count + label_job_count} 个任务")
                
                if doc_job_count > 0 and label_job_count == 0:
                    print(f"\n❌ 问题确认:")
                    print(f"   所有任务都在发货单打印机上")
                    print(f"   标签打印机没有任务")
                    print(f"   这说明标签打印任务被错误地发送到发货单打印机")
                    
                    print(f"\n💡 可能的原因:")
                    print(f"   1. ShellExecute参数格式错误")
                    print(f"   2. 打印机选择逻辑有误")
                    print(f"   3. PDF应用自动选择默认打印机")
                    print(f"   4. 临时更改默认打印机失败")
                    
                elif doc_job_count > 0 and label_job_count > 0:
                    print(f"\n✅ 打印任务分配正确:")
                    print(f"   发货单在 Jolimark")
                    print(f"   标签在 TSC")
                    print(f"   任务正确分配到不同的打印机")
                    
                else:
                    print(f"\n⚠️ 打印队列为空:")
                    print(f"   可能原因:")
                    print(f"   1. 打印任务已处理完成")
                    print(f"   2. 打印机未连接")
                    print(f"   3. 打印任务发送失败")
                
                return True
                
            else:
                print(f"❌ 订单生成失败: {response.status_code}")
                print(f"响应内容: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 发送请求失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def add_detailed_logging():
    """添加详细日志到打印函数"""
    print("\n" + "=" * 80)
    print("🔧 添加详细日志到打印函数")
    print("=" * 80)
    
    try:
        # 检查print_utils.py中的打印函数
        with open('print_utils.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已有详细日志
        if "logger.info(f\"实际调用ShellExecute: {result}\"" not in content:
            print("⚠️ 打印函数中缺少详细日志")
            print("💡 建议：在ShellExecute调用前后添加详细日志")
            
            # 找到ShellExecute调用位置
            if 'win32api.ShellExecute' in content:
                print("✅ 找到ShellExecute调用")
                print("📝 可以在此处添加详细日志")
                print("   logger.info(f\"文件路径: {file_path}\")")
                print("   logger.info(f\"打印机名称: {printer_name}\")")
                print("   logger.info(f\"ShellExecute操作: print\")")
                print("   result = win32api.ShellExecute(...)")
                print("   logger.info(f\"ShellExecute结果: {result}\")")
            else:
                print("⚠️ 未找到ShellExecute调用")
        else:
            print("✅ 打印函数中已有详细日志")
        
        # 检查printer_automation.py
        with open('printer_automation.py', 'r', encoding='utf-8') as f:
            auto_content = f.read()
        
        if "logger.info" in auto_content:
            print("✅ printer_automation.py中有日志记录")
        else:
            print("⚠️ printer_automation.py中可能缺少日志")
        
        return True
        
    except Exception as e:
        print(f"❌ 检查日志配置失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始打印任务分配测试...")
    
    # 运行测试
    test_success = test_print_job_distribution()
    
    # 添加详细日志建议
    log_success = add_detailed_logging()
    
    print("\n" + "=" * 80)
    print("🎉 测试完成")
    print("=" * 80)
    
    if test_success:
        print("✅ 打印任务分配测试完成")
    else:
        print("❌ 打印任务分配测试失败")
    
    if log_success:
        print("✅ 日志配置检查完成")
    
    print("\n💡 下一步操作:")
    print("   1. 运行测试脚本观察打印任务分配情况")
    print("   2. 根据分析结果采取相应措施")
    print("   3. 如果问题仍然存在，添加更详细的日志")
