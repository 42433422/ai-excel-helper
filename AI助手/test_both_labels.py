#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同时生成有剂和无剂的两种标签进行对比
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

# 测试数据1 - 包含"剂"的产品（无参考配比）
test_data_with_ji = {
    'product_number': 'HL-555',
    'product_name': 'PU固化剂',  # 包含"剂"，应该不显示参考配比
    'ratio': '1:0.5-0.6:0.5-0.8',
    'production_date': '2026.02.01',
    'shelf_life': '6个月',
    'specification': '15±0.1KG',
    'inspector': '合格'
}

# 测试数据2 - 不包含"剂"的产品（有参考配比）
test_data_without_ji = {
    'product_number': 'HL-444',
    'product_name': 'PU净味三分光清面漆',  # 不包含"剂"，应该显示参考配比
    'ratio': '1:0.5-0.6:0.5-0.8',
    'production_date': '2026.02.01',
    'shelf_life': '6个月',
    'specification': '20±0.1KG',
    'inspector': '合格'
}

print("=== 同时生成两种标签进行对比 ===")

# 生成标签
generator = ProductLabelGenerator()

# 生成有剂标签（无参考配比）
filename1 = f"with_ji_no_ratio_{uuid.uuid4().hex[:8]}.png"
output_path1 = os.path.join(LABELS_EXPORT_DIR, filename1)
generator.generate_label(test_data_with_ji, output_path1)

# 生成无剂标签（有参考配比）
filename2 = f"without_ji_with_ratio_{uuid.uuid4().hex[:8]}.png"
output_path2 = os.path.join(LABELS_EXPORT_DIR, filename2)
generator.generate_label(test_data_without_ji, output_path2)

if os.path.exists(output_path1) and os.path.exists(output_path2):
    print(f"✅ 两种标签生成成功")
    print(f"📁 有剂标签: {filename1}")
    print(f"📁 无剂标签: {filename2}")
    print()
    print("标签对比:")
    print("=" * 50)
    print()
    print("📄 有剂标签（无参考配比）:")
    print(f"产品名称: {test_data_with_ji['product_name']}")
    print(f"是否包含'剂': {'是' if any(kw in test_data_with_ji['product_name'] for kw in ['剂', '料']) else '否'}")
    print("特点:")
    print("✅ 不显示参考配比区域")
    print("✅ 不显示搅拌提示文字")
    print("✅ 5个区域均匀分布")
    print("✅ 字体增大")
    print()
    print("📄 无剂标签（有参考配比）:")
    print(f"产品名称: {test_data_without_ji['product_name']}")
    print(f"是否包含'剂': {'是' if any(kw in test_data_without_ji['product_name'] for kw in ['剂', '料']) else '否'}")
    print("特点:")
    print("✅ 显示参考配比区域")
    print("✅ 显示搅拌提示文字")
    print("✅ 保持原有布局")
    print("✅ 字体增大")
    print()
    print("请查看两个标签文件，对比效果:")
    print("1. 有剂标签是否正确显示5个区域布局")
    print("2. 无剂标签是否正确显示参考配比")
    print("3. 两种标签的字体是否都明显增大")
    print("4. 整体视觉效果是否满意")
else:
    print(f"❌ 标签生成失败")
    if not os.path.exists(output_path1):
        print("❌ 有剂标签生成失败")
    if not os.path.exists(output_path2):
        print("❌ 无剂标签生成失败")
