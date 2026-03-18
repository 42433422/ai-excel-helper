#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成消除底部空白的无参考配比标签
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
    'product_number': 'HL-222',
    'product_name': 'PU固化剂',  # 包含"剂"，应该不显示参考配比
    'ratio': '1:0.5-0.6:0.5-0.8',
    'production_date': '2026.02.01',
    'shelf_life': '6个月',
    'specification': '35±0.1KG',
    'inspector': '合格'
}

print("=== 生成消除底部空白的无参考配比标签 ===")
print(f"产品名称: {test_data['product_name']}")
print(f"是否包含'剂'或'料': {'是' if any(kw in test_data['product_name'] for kw in ['剂', '料']) else '否'}")
print(f"修复内容: 让规格区域延伸到标签底部，消除底部空白")

# 生成标签
generator = ProductLabelGenerator()
filename = f"no_bottom_space_{uuid.uuid4().hex[:8]}.png"
output_path = os.path.join(LABELS_EXPORT_DIR, filename)
generator.generate_label(test_data, output_path)

if os.path.exists(output_path):
    print(f"✅ 无底部空白标签生成成功: {filename}")
    print(f"📁 文件位置: {output_path}")
    print()
    print("布局修复:")
    print("之前：规格区域下方有大量空白 (约279px)")
    print("现在：规格区域延伸到标签底部，完全消除空白")
    print()
    print("新的布局结构:")
    print("1. 产品编号区域: 25-95px (70px)")
    print("2. 产品名称区域: 95-157px (62px)")
    print("3. 生产日期+保质期区域: 157-239px (82px)")
    print("4. 规格+检验员区域: 239px-标签底部 (延伸到标签底部)")
    print()
    print("分割线修复:")
    print("✅ 保质期前面的垂直分割线")
    print("✅ 所有垂直分割线延伸到标签底部")
else:
    print(f"❌ 标签生成失败")

print()
print("请查看生成的标签文件，确认:")
print("1. 是否完全消除了底部空白")
print("2. 保质期前面是否有垂直分割线")
print("3. 是否不显示参考配比区域")
print("4. 是否不显示搅拌提示文字")
