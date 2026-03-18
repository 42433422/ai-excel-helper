#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证当前打印顺序的测试脚本
"""

import os
import sys
sys.path.append(os.path.dirname(__file__))

def test_printing_order():
    """
    测试当前打印顺序
    """
    print("=" * 60)
    print("🔍 当前打印顺序验证")
    print("=" * 60)
    
    # 读取app_api.py文件中的打印相关代码
    api_file = "app_api.py"
    
    print("\n📄 当前打印顺序分析:")
    print("1. 发货单生成API (/api/generate)")
    
    try:
        with open(api_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 查找打印相关的代码段
        lines = content.split('\n')
        
        printing_order = []
        for i, line in enumerate(lines):
            if "# 1. 打印发货单" in line:
                printing_order.append(("发货单打印", i+1, line.strip()))
            elif "# 2. 打印标签" in line:
                printing_order.append(("标签打印", i+1, line.strip()))
            elif "开始自动打印发货单和标签" in line:
                printing_order.append(("打印开始", i+1, line.strip()))
            elif "开始为订单" in line and "转换标签为PDF" in line:
                printing_order.append(("标签转换", i+1, line.strip()))
        
        print("\n📋 打印顺序详情:")
        for item_type, line_num, content in printing_order:
            print(f"  {item_type} - 第{line_num}行: {content}")
        
        # 分析顺序
        document_index = -1
        label_index = -1
        
        for i, (item_type, _, _) in enumerate(printing_order):
            if item_type == "发货单打印":
                document_index = i
            elif item_type == "标签打印":
                label_index = i
        
        print(f"\n🔍 顺序分析:")
        print(f"  发货单打印位置: 第{document_index + 1}项")
        print(f"  标签打印位置: 第{label_index + 1}项")
        
        if document_index != -1 and label_index != -1:
            if document_index < label_index:
                print(f"\n✅ 当前顺序正确: 发货单 → 标签")
            else:
                print(f"\n❌ 当前顺序错误: 标签 → 发货单")
                print(f"   需要调整为: 发货单 → 标签")
        else:
            print(f"\n⚠️  未能找到完整的打印顺序")
            
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
    
    print("\n" + "=" * 60)
    print("验证完成")
    print("=" * 60)

if __name__ == "__main__":
    test_printing_order()
