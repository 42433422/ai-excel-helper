#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试动态打印机获取功能
"""

import os
import sys
sys.path.append(os.path.dirname(__file__))

# 导入动态打印机获取函数
from app_api import get_document_printer, get_label_printer

def test_dynamic_printer_detection():
    """
    测试动态打印机获取功能
    """
    print("=" * 60)
    print("🖨️ 动态打印机获取测试")
    print("=" * 60)
    
    # 1. 测试发货单打印机获取
    print("\n📄 1. 测试发货单打印机获取")
    document_printer = get_document_printer()
    print(f"   获取结果: {document_printer}")
    
    if document_printer:
        print(f"   ✅ 成功获取发货单打印机")
    else:
        print(f"   ❌ 未能获取发货单打印机")
    
    # 2. 测试标签打印机获取
    print("\n🏷️ 2. 测试标签打印机获取")
    label_printer = get_label_printer()
    print(f"   获取结果: {label_printer}")
    
    if label_printer:
        print(f"   ✅ 成功获取标签打印机")
    else:
        print(f"   ❌ 未能获取标签打印机")
    
    # 3. 验证打印机分离
    print("\n🔍 3. 验证打印机分离")
    
    if document_printer and label_printer:
        if document_printer != label_printer:
            print(f"   ✅ 发货单打印机 ≠ 标签打印机")
            print(f"   📄 发货单: {document_printer}")
            print(f"   🏷️  标签: {label_printer}")
        else:
            print(f"   ⚠️  发货单打印机 = 标签打印机")
            print(f"   🚨 这可能会导致任务混乱")
    
    # 4. 验证识别逻辑
    print("\n🧠 4. 验证识别逻辑")
    print("   发货单打印机识别关键词: ['joli', '24-pin', 'dot matrix', 'impact', 'lq', '针式']")
    print("   标签打印机识别关键词: ['tsc', 'ttp', 'label', '标签', 'thermal', 'barcode']")
    
    # 5. 最终建议
    print("\n💡 5. 最终建议")
    
    if document_printer and label_printer and document_printer != label_printer:
        print("   ✅ 动态打印机获取功能正常工作")
        print("   ✅ 发货单和标签打印机已正确分离")
        print("   ✅ 不再依赖硬编码的打印机名称")
    else:
        print("   ⚠️  需要检查打印机识别逻辑")
        print("   ⚠️  可能需要手动配置打印机")

if __name__ == "__main__":
    test_dynamic_printer_detection()
