#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成恢复居中逻辑的无参考配比标签
"""

import os
import sys

# 添加当前目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from label_generator import ProductLabelGenerator
from datetime import datetime
import uuid

# 商标导出目录
LABELS_EXPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '商标导出')
os.makedirs(LABELS_EXPORT_DIR, exist_ok=True)

# 测试数据 - 包含"剂"的产品（无参考配比）
test_data = {
    'product_number': 'HL-666',  # 较短的产品编号
    'product_name': 'PU固化剂',  # 包含"剂"，应该不显示参考配比
    'ratio': '1:0.5-0.6:0.5-0.8',
    'production_date': '2026.02.01',
    'shelf_life': '6个月',
    'specification': '90±0.1KG',
    'inspector': '合格'
}

print("=== 生成恢复居中逻辑的无参考配比标签 ===")
print(f"产品名称: {test_data['product_name']}")
print(f"是否包含'剂'或'料': {'是' if any(kw in test_data['product_name'] for kw in ['剂', '料']) else '否'}")
print(f"修复内容: 恢复产品编号和产品名称数值部分的居中逻辑")

# 生成标签
generator = ProductLabelGenerator()
filename = f"recovered_centered_{uuid.uuid4().hex[:8]}.png"
output_path = os.path.join(LABELS_EXPORT_DIR, filename)
generator.generate_label(test_data, output_path)

if os.path.exists(output_path):
    print(f"✅ 恢复居中逻辑标签生成成功: {filename}")
    print(f"📁 文件位置: {output_path}")
    print()
    print("居中逻辑修复:")
    print("错误：我把数值固定在210的位置")
    print("正确：恢复原来的居中逻辑，在680px宽区域居中")
    print()
    print("恢复的内容:")
    print("✅ 产品编号数值: 200 + (680 - pn_value_width) // 2")
    print("✅ 产品名称数值: 200 + (680 - name_value_width) // 2")
    print("✅ 只增大字体，保持原有居中逻辑")
else:
    print(f"❌ 标签生成失败")

print()
print("请查看生成的标签文件，确认:")
print("1. 产品编号数值是否在680px宽区域内居中")
print("2. 产品名称数值是否在680px宽区域内居中")
print("3. 字体是否明显增大")
