#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整打印测试：验证发货单和标签分别发送到正确的打印机
"""

import os
import sys
sys.path.append(os.path.dirname(__file__))

from print_utils import print_document

def test_complete_printing():
    """
    测试完整的打印流程
    """
    print("=" * 60)
    print("🖨️  完整打印测试")
    print("=" * 60)
    
    # 1. 测试发货单打印
    print("\n📄 1. 测试发货单打印")
    print("   目标: Jolimark 24-pin printer")
    
    # 查找一个文档文件进行测试
    doc_files = [f for f in os.listdir('.') if f.endswith(('.doc', '.docx', '.pdf'))]
    test_doc = None
    
    for file in doc_files:
        if '发货单' in file or 'order' in file.lower() or file.endswith('.pdf'):
            test_doc = file
            break
    
    if test_doc:
        print(f"   测试文件: {test_doc}")
        doc_result = print_document(test_doc, "Jolimark 24-pin printer")
        print(f"   结果: {'✅ 成功' if doc_result.get('success') else '❌ 失败'}")
        print(f"   打印机: {doc_result.get('printer', '未知')}")
        print(f"   方法: {doc_result.get('method', '未知')}")
    else:
        print("   ❌ 未找到适合的测试文档")
    
    # 2. 测试标签打印
    print("\n🏷️ 2. 测试标签打印")
    print("   目标: TSC TTP-244 Plus")
    
    # 查找PDF文件
    pdf_files = [f for f in os.listdir('.') if f.endswith('.pdf')]
    test_pdf = None
    
    for file in pdf_files:
        if '商标' in file or '标签' in file or 'label' in file.lower():
            test_pdf = file
            break
    
    if test_pdf:
        print(f"   测试文件: {test_pdf}")
        label_result = print_document(test_pdf, "TSC TTP-244 Plus")
        print(f"   结果: {'✅ 成功' if label_result.get('success') else '❌ 失败'}")
        print(f"   打印机: {label_result.get('printer', '未知')}")
        print(f"   方法: {label_result.get('method', '未知')}")
    else:
        print("   ❌ 未找到适合的测试PDF文件")
    
    # 3. 验证打印机分配
    print("\n🔍 3. 验证打印机分配")
    print("   期望:")
    print("   📄 发货单 → Jolimark 24-pin printer")
    print("   🏷️  标签 → TSC TTP-244 Plus")
    print()
    
    # 检查结果
    if test_doc and doc_result:
        print(f"   📄 发货单测试: {'✅ 正确' if doc_result.get('printer') == 'Jolimark 24-pin printer' else '❌ 错误'}")
        if doc_result.get('printer') != 'Jolimark 24-pin printer':
            print(f"      实际发送到: {doc_result.get('printer')}")
    
    if test_pdf and label_result:
        print(f"   🏷️  标签测试: {'✅ 正确' if label_result.get('printer') == 'TSC TTP-244 Plus' else '❌ 错误'}")
        if label_result.get('printer') != 'TSC TTP-244 Plus':
            print(f"      实际发送到: {label_result.get('printer')}")
    
    # 4. 总结
    print("\n📊 4. 测试总结")
    
    doc_ok = test_doc and doc_result and doc_result.get('success') and doc_result.get('printer') == 'Jolimark 24-pin printer'
    label_ok = test_pdf and label_result and label_result.get('success') and label_result.get('printer') == 'TSC TTP-244 Plus'
    
    if doc_ok and label_ok:
        print("   ✅ 所有测试通过！打印任务分配正确！")
    elif doc_ok:
        print("   ⚠️  发货单测试通过，标签测试失败")
    elif label_ok:
        print("   ⚠️  标签测试通过，发货单测试失败")
    else:
        print("   ❌ 所有测试都失败了")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_complete_printing()
