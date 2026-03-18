#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成均匀分布布局的无参考配比标签
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
    'product_number': 'HL-666',
    'product_name': 'PU固化剂',  # 包含"剂"，应该不显示参考配比
    'ratio': '1:0.5-0.6:0.5-0.8',
    'production_date': '2026.02.01',
    'shelf_life': '6个月',
    'specification': '15±0.1KG',
    'inspector': '合格'
}

print("=== 生成均匀分布布局的无参考配比标签 ===")
print(f"产品名称: {test_data['product_name']}")
print(f"是否包含'剂'或'料': {'是' if any(kw in test_data['product_name'] for kw in ['剂', '料']) else '否'}")
print(f"布局改进: 4个区域均匀分布，完全利用800px标签高度")

# 生成标签
generator = ProductLabelGenerator()
filename = f"uniform_layout_{uuid.uuid4().hex[:8]}.png"
output_path = os.path.join(LABELS_EXPORT_DIR, filename)
generator.generate_label(test_data, output_path)

if os.path.exists(output_path):
    print(f"✅ 均匀分布标签生成成功: {filename}")
    print(f"📁 文件位置: {output_path}")
    print()
    print("布局对比:")
    print("之前：4个区域 + 大面积底部空白 (约458px)")
    print("现在：4个区域均匀分布 (每个约180px) + 最小空白")
    print()
    print("现在的效果应该:")
    print("1. 4个区域高度相等 (~180px)")
    print("2. 垂直分割线延伸到标签底部")
    print("3. 完全利用标签空间，无大面积空白")
else:
    print(f"❌ 标签生成失败")

print()
print("请查看生成的标签文件，确认:")
print("1. 4个区域是否均匀分布")
print("2. 是否不显示参考配比区域")
print("3. 是否不显示搅拌提示文字")
print("4. 是否充分利用了标签空间")
