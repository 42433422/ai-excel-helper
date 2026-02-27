#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试生成无参考配比的标签
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

# 测试数据 - 包含"剂"的产品
test_data_with_agent = {
    'product_number': 'HL-002',
    'product_name': 'PU固化剂',  # 包含"剂"
    'ratio': '1:0.5-0.6:0.5-0.8',
    'production_date': '2026.02.01',
    'shelf_life': '6个月',
    'specification': '5±0.1KG',
    'inspector': '合格'
}

# 测试数据 - 不包含"剂"或"料"的产品
test_data_without_agent = {
    'product_number': 'HL-001',
    'product_name': 'PU净味哑光白面漆',  # 不包含"剂"或"料"
    'ratio': '1:0.5-0.6:0.5-0.8',
    'production_date': '2026.02.01',
    'shelf_life': '6个月',
    'specification': '20±0.1KG',
    'inspector': '合格'
}

print("=== 测试标签生成功能 ===")

# 生成无参考配比的标签
print("1. 生成无参考配比的标签 (包含'剂')...")
generator = ProductLabelGenerator()
filename1 = f"test_label_no_ratio_{uuid.uuid4().hex[:8]}.png"
output_path1 = os.path.join(LABELS_EXPORT_DIR, filename1)
generator.generate_label(test_data_with_agent, output_path1)

if os.path.exists(output_path1):
    print(f"✅ 无配比标签生成成功: {filename1}")
    print(f"   产品名称: {test_data_with_agent['product_name']}")
    print(f"   是否包含'剂'或'料': {'是' if any(kw in test_data_with_agent['product_name'] for kw in ['剂', '料']) else '否'}")
    print(f"   预期: 应该不显示参考配比区域")
else:
    print(f"❌ 无配比标签生成失败")

print()

# 生成有参考配比的标签
print("2. 生成有参考配比的标签 (不包含'剂'或'料')...")
filename2 = f"test_label_with_ratio_{uuid.uuid4().hex[:8]}.png"
output_path2 = os.path.join(LABELS_EXPORT_DIR, filename2)
generator.generate_label(test_data_without_agent, output_path2)

if os.path.exists(output_path2):
    print(f"✅ 有配比标签生成成功: {filename2}")
    print(f"   产品名称: {test_data_without_agent['product_name']}")
    print(f"   是否包含'剂'或'料': {'是' if any(kw in test_data_without_agent['product_name'] for kw in ['剂', '料']) else '否'}")
    print(f"   预期: 应该显示参考配比区域")
else:
    print(f"❌ 有配比标签生成失败")

print()
print("=== 标签生成完成 ===")
print(f"标签保存在: {LABELS_EXPORT_DIR}")
print("请检查生成的标签文件:")
print(f"1. 无配比标签: {filename1}")
print(f"2. 有配比标签: {filename2}")
