#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试用户提供的订单格式
七彩乐园一桶PE白底漆规格28
"""

import os
import sys
import json
import time
import requests

def test_user_order_format():
    """测试用户提供的订单格式"""
    print("=" * 80)
    print("🚀 测试用户订单格式")
    print("=" * 80)
    
    try:
        # 1. 检查Flask应用状态
        print("\n📋 1. 检查Flask应用状态")
        try:
            response = requests.get("http://127.0.0.1:5000/api/printers", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Flask应用正常运行")
            else:
                print(f"❌ Flask应用状态异常: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 无法连接Flask应用: {e}")
            return False
        
        # 2. 使用用户提供的订单格式
        print("\n📋 2. 测试用户订单格式")
        
        order_text = "七彩乐园一桶PE白底漆规格28"
        
        print(f"订单文本: {order_text}")
        
        test_order = {
            "order_text": order_text,
            "template_name": "尹玉华1.xlsx",
            "custom_mode": False,
            "number_mode": False,
            "excel_sync": False,
            "auto_print": True  # 启用自动打印
        }
        
        print(f"\n📤 发送请求...")
        print(f"自动打印: {test_order['auto_print']}")
        
        # 3. 发送请求
        try:
            response = requests.post(
                "http://127.0.0.1:5000/api/generate",
                json=test_order,
                timeout=90  # 延长超时时间
            )
            
            print(f"\n📥 收到响应:")
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"成功: {result.get('success')}")
                
                if result.get('success'):
                    print(f"\n✅ 订单生成成功！")
                    
                    # 显示解析结果
                    if 'parsed_data' in result:
                        parsed = result['parsed_data']
                        print(f"\n📊 解析结果:")
                        print(f"   购买单位: {parsed.get('purchase_unit', '未知')}")
                        print(f"   产品数: {len(parsed.get('products', []))}")
                        
                        products = parsed.get('products', [])
                        for j, product in enumerate(products):
                            print(f"\n   产品{j+1}:")
                            print(f"     名称: {product.get('name', '未知')}")
                            print(f"     型号: {product.get('model_number', '未知')}")
                            print(f"     规格: {product.get('specification', '未知')}")
                            print(f"     数量(罐): {product.get('quantity_tins', 0)}")
                            print(f"     数量(KG): {product.get('quantity_kg', 0)}")
                            print(f"     单价: {product.get('unit_price', 0)}")
                            print(f"     金额: {product.get('amount', 0)}")
                    
                    # 显示生成的文件
                    if 'document' in result:
                        doc = result['document']
                        print(f"\n📄 生成的发货单:")
                        print(f"   文件名: {doc.get('filename', '未知')}")
                    
                    # 显示标签
                    if 'labels' in result:
                        labels = result['labels']
                        print(f"\n🏷️ 生成的标签: {len(labels)} 个")
                        for i, label in enumerate(labels):
                            print(f"   标签{i+1}: {label.get('filename', '未知')}")
                    
                    # 检查打印结果（这是重点）
                    if 'printing' in result:
                        printing = result['printing']
                        print(f"\n🖨️ 打印结果:")
                        print(f"   发货单打印: {printing.get('document_printed', False)}")
                        print(f"   标签打印: {printing.get('labels_printed', 0)}")
                        print(f"   发货单结果: {printing.get('document_result', '未知')}")
                        print(f"   标签结果: {printing.get('labels_result', '未知')}")
                        
                        # 这是关键：检查打印机分配
                        doc_result = printing.get('document_result', '')
                        label_result = printing.get('labels_result', '')
                        
                        print(f"\n🔍 打印机分配检查:")
                        if 'Jolimark' in str(doc_result):
                            print(f"   ✅ 发货单发送到 Jolimark 24-pin printer")
                        else:
                            print(f"   ❌ 发货单打印机: {doc_result}")
                        
                        if 'TSC' in str(label_result):
                            print(f"   ✅ 标签发送到 TSC TTP-244 Plus")
                        elif printing.get('labels_printed', 0) > 0:
                            print(f"   ℹ️ 标签打印了 {printing.get('labels_printed')} 个")
                        else:
                            print(f"   ❌ 标签打印机: {label_result}")
                        
                else:
                    print(f"\n❌ 订单生成失败")
                    print(f"   消息: {result.get('message', '未知')}")
                    
                    # 显示解析结果
                    if 'parsed_data' in result:
                        parsed = result['parsed_data']
                        print(f"\n📊 解析结果:")
                        print(f"   产品数: {len(parsed.get('products', []))}")
                        if not parsed.get('products'):
                            print(f"   ⚠️ 没有解析到产品")
                            print(f"   原始文本: {parsed.get('raw_text', '无')}")
                    
            else:
                print(f"\n❌ HTTP错误: {response.status_code}")
                print(f"响应内容: {response.text[:500]}")
                
        except Exception as e:
            print(f"\n❌ 请求失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 4. 检查打印机队列
        print("\n" + "=" * 80)
        print("📋 3. 检查打印机队列")
        print("=" * 80)
        
        time.sleep(2)  # 等待任务进入队列
        
        try:
            import win32print
            
            # 检查发货单打印机
            doc_printer = "Jolimark 24-pin printer"
            try:
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
                print(f"   ❌ 检查失败: {e}")
            
            # 检查标签打印机
            label_printer = "TSC TTP-244 Plus"
            try:
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
                print(f"   ❌ 检查失败: {e}")
            
            # 分析结果
            doc_job_count = len(doc_jobs) if 'doc_jobs' in dir() else 0
            label_job_count = len(label_jobs) if 'label_jobs' in dir() else 0
            
            print(f"\n📊 打印机任务统计:")
            print(f"   发货单打印机: {doc_job_count} 个任务")
            print(f"   标签打印机: {label_job_count} 个任务")
            
            if doc_job_count > 0 and label_job_count == 0:
                print(f"\n❌ 问题确认:")
                print(f"   所有任务都在发货单打印机上")
                print(f"   标签打印机没有任务")
                print(f"   这说明标签任务被错误地发送到了发货单打印机")
            
            elif doc_job_count > 0 and label_job_count > 0:
                print(f"\n✅ 任务分配正确:")
                print(f"   发货单 → Jolimark")
                print(f"   标签 → TSC")
            
        except Exception as e:
            print(f"❌ 检查打印机队列失败: {e}")
        
        # 5. 总结
        print("\n" + "=" * 80)
        print("📊 测试总结")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始测试用户订单格式...")
    print(f"订单: 七彩乐园一桶PE白底漆规格28")
    print()
    
    # 运行测试
    test_user_order_format()
    
    print("\n" + "=" * 80)
    print("🎉 测试完成")
    print("=" * 80)
