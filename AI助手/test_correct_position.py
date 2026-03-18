#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成增大字体但位置正确的无参考配比标签
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
    'product_number': 'HL-777',
    'product_name': 'PU固化剂',  # 包含"剂"，应该不显示参考配比
    'ratio': '1:0.5-0.6:0.5-0.8',
    'production_date': '2026.02.01',
    'shelf_life': '6个月',
    'specification': '80±0.1KG',
    'inspector': '合格'
}

print("=== 生成增大字体但位置正确的无参考配比标签 ===")
print(f"产品名称: {test_data['product_name']}")
print(f"是否包含'剂'或'料': {'是' if any(kw in test_data['product_name'] for kw in ['剂', '料']) else '否'}")
print(f"修正内容: 恢复原来的位置，只增大字体")

# 生成标签
generator = ProductLabelGenerator()
filename = f"correct_position_larger_font_{uuid.uuid4().hex[:8]}.png"
output_path = os.path.join(LABELS_EXPORT_DIR, filename)
generator.generate_label(test_data, output_path)

if os.path.exists(output_path):
    print(f"✅ 位置正确字体增大标签生成成功: {filename}")
    print(f"📁 文件位置: {output_path}")
    print()
    print("修正对比:")
    print("错误：改变了位置，还做了纵向居中")
    print("正确：恢复原来的位置，只增大字体")
    print()
    print("字体大小调整:")
    print("✅ 产品编号标签: 32 → 40")
    print("✅ 产品编号数值: 54 → 60")
    print("✅ 产品名称标签: 32 → 40")
    print("✅ 产品名称数值: 42 → 48")
    print("✅ 生产日期/保质期/规格/检验员: 32 → 38")
    print()
    print("位置恢复:")
    print("✅ 产品编号: 45, 210 → y_pn + 12")
    print("✅ 产品名称: 45, 210 → y_name + 12")
    print("✅ 生产日期/保质期: 45, 210, 520, 670 → y_date + 12")
    print("✅ 规格/检验员: 45, 210, 520, 670 → y_spec + 12")
else:
    print(f"❌ 标签生成失败")

print()
print("请查看生成的标签文件，确认:")
print("1. 位置是否恢复到原来的正确位置")
print("2. 字体是否明显增大")
print("3. 整体效果是否满意")
