#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试完整的PDF生成和打印流程
"""

import os
import sys
import requests
import json
import time
sys.path.append(os.path.dirname(__file__))

def test_complete_pdf_workflow():
    """
    测试完整的PDF生成和打印工作流
    """
    print("=" * 60)
    print("🧪 完整PDF生成和打印测试")
    print("=" * 60)
    
    # 测试数据
    test_order_data = {
        "order_text": "订单: 26-0200111A\n日期: 2026-02-02\n客户: 测试客户\n产品: 清洁剂\n型号: CX-001\n数量: 10件\n单价: 15.00元\n金额: 150.00元",
        "template_name": "尹玉华1.xlsx"
    }
    
    print("1. 测试订单数据:")
    for key, value in test_order_data.items():
        print(f"   {key}: {value[:50]}{'...' if len(str(value)) > 50 else ''}")
    print()
    
    # 步骤1: 生成发货单和标签
    print("2. 生成发货单和标签...")
    try:
        response = requests.post('http://127.0.0.1:5000/api/generate', 
                                json=test_order_data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print("   ✅ API调用成功")
            
            if result.get('success'):
                print(f"   ✅ 发货单生成成功")
                print(f"   ✅ 生成标签数量: {len(result.get('labels', []))}")
                
                # 检查打印结果
                printing_info = result.get('printing', {})
                if printing_info:
                    print(f"   📄 发货单打印: {'✅' if printing_info.get('document_printed') else '❌'}")
                    print(f"   🏷️  标签打印: {printing_info.get('labels_printed', 0)} 个")
                    
                return result
            else:
                print(f"   ❌ API返回错误: {result.get('message', 'Unknown error')}")
                return None
        else:
            print(f"   ❌ HTTP错误: {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ 网络请求失败: {e}")
        return None
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        return None

def test_pdf_files():
    """
    测试PDF文件生成和存在性
    """
    print("\n3. 检查PDF文件...")
    
    pdf_dir = "PDF文件"
    if not os.path.exists(pdf_dir):
        print(f"   ❌ PDF文件夹不存在: {pdf_dir}")
        return
    
    # 查找新生成的PDF文件（最近几分钟内）
    recent_pdfs = []
    current_time = time.time()
    
    for file in os.listdir(pdf_dir):
        if file.endswith('.pdf'):
            file_path = os.path.join(pdf_dir, file)
            file_time = os.path.getmtime(file_path)
            if current_time - file_time < 300:  # 5分钟内
                recent_pdfs.append(file)
    
    if recent_pdfs:
        print(f"   ✅ 找到 {len(recent_pdfs)} 个最近的PDF文件:")
        for pdf in recent_pdfs:
            size = os.path.getsize(os.path.join(pdf_dir, pdf)) / 1024
            print(f"      - {pdf} ({size:.1f} KB)")
    else:
        print(f"   ⚠️  未找到最近的PDF文件")
        print(f"   📁 PDF文件夹内容:")
        for file in os.listdir(pdf_dir)[:5]:  # 显示前5个
            if file.endswith('.pdf'):
                print(f"      - {file}")

def test_pdf_printing():
    """
    测试PDF打印功能
    """
    print("\n4. 测试PDF打印功能...")
    
    # 查找现有的PDF文件进行测试
    pdf_dir = "PDF文件"
    test_pdf = None
    
    if os.path.exists(pdf_dir):
        for file in os.listdir(pdf_dir):
            if file.endswith('.pdf') and '26-020' in file:
                test_pdf = os.path.join(pdf_dir, file)
                break
    
    if test_pdf:
        print(f"   测试PDF文件: {os.path.basename(test_pdf)}")
        print(f"   文件大小: {os.path.getsize(test_pdf) / 1024:.1f} KB")
        
        # 测试打印
        try:
            from pdf_label_printer import print_pdf_labels
            result = print_pdf_labels(test_pdf, 1)
            
            if result.get('success'):
                print(f"   ✅ PDF打印成功")
                print(f"   📊 打印机: {result.get('printer', 'Unknown')}")
                print(f"   📄 方法: {result.get('method', 'Unknown')}")
            else:
                print(f"   ❌ PDF打印失败: {result.get('message', 'Unknown error')}")
                
        except Exception as e:
            print(f"   ❌ 打印测试失败: {e}")
    else:
        print(f"   ❌ 未找到适合的测试PDF文件")

def main():
    """
    主函数
    """
    print("开始完整PDF生成和打印流程测试...")
    
    # 测试1: 完整工作流
    result = test_complete_pdf_workflow()
    
    # 等待一下让系统有时间生成文件
    print("\n⏳ 等待系统处理...")
    time.sleep(3)
    
    # 测试2: 检查PDF文件
    test_pdf_files()
    
    # 测试3: 测试打印
    test_pdf_printing()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
