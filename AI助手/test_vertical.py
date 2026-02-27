#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成修复垂直分割线的无参考配比标签
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
    'product_number': 'HL-333',
    'product_name': 'PU固化剂',  # 包含"剂"，应该不显示参考配比
    'ratio': '1:0.5-0.6:0.5-0.8',
    'production_date': '2026.02.01',
    'shelf_life': '6个月',
    'specification': '30±0.1KG',
    'inspector': '合格'
}

print("=== 生成修复垂直分割线的无参考配比标签 ===")
print(f"产品名称: {test_data['product_name']}")
print(f"是否包含'剂'或'料': {'是' if any(kw in test_data['product_name'] for kw in ['剂', '料']) else '否'}")
print(f"修复内容: 添加保质期前面的垂直分割线")

# 生成标签
generator = ProductLabelGenerator()
filename = f"fixed_vertical_line_{uuid.uuid4().hex[:8]}.png"
output_path = os.path.join(LABELS_EXPORT_DIR, filename)
generator.generate_label(test_data, output_path)

if os.path.exists(output_path):
    print(f"✅ 垂直分割线修复标签生成成功: {filename}")
    print(f"📁 文件位置: {output_path}")
    print()
    print("修复内容:")
    print("之前：无参考配比标签保质期前面缺少垂直分割线")
    print("现在：添加保质期前面的垂直分割线，保持原来的4个区域布局")
    print()
    print("分割线修复:")
    print("✅ 左边分割线（延伸到标签底部）")
    print("✅ 右边分割线（延伸到标签底部）")
    print("✅ 保质期前面的垂直分割线（延伸到标签底部）")
else:
    print(f"❌ 标签生成失败")

print()
print("请查看生成的标签文件，确认:")
print("1. 保质期前面是否有垂直分割线")
print("2. 是否保持原来的4个区域布局")
print("3. 是否不显示参考配比区域")
print("4. 是否不显示搅拌提示文字")
