#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成优化后的无参考配比标签进行测试
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
    'product_number': 'HL-888',
    'product_name': 'PU固化剂',  # 包含"剂"，应该不显示参考配比
    'ratio': '1:0.5-0.6:0.5-0.8',
    'production_date': '2026.02.01',
    'shelf_life': '6个月',
    'specification': '8±0.1KG',
    'inspector': '合格'
}

print("=== 生成优化后的无参考配比标签 ===")
print(f"产品名称: {test_data['product_name']}")
print(f"是否包含'剂'或'料': {'是' if any(kw in test_data['product_name'] for kw in ['剂', '料']) else '否'}")
print(f"预期效果: 不显示参考配比，纵向分布更紧凑")

# 生成标签
generator = ProductLabelGenerator()
filename = f"optimized_label_{uuid.uuid4().hex[:8]}.png"
output_path = os.path.join(LABELS_EXPORT_DIR, filename)
generator.generate_label(test_data, output_path)

if os.path.exists(output_path):
    print(f"✅ 优化标签生成成功: {filename}")
    print(f"📁 文件位置: {output_path}")
    print()
    print("优化效果对比:")
    print("之前：无配比标签区域间距大，底部空白多")
    print("现在：纵向分布更紧凑，整体布局更平衡")
else:
    print(f"❌ 标签生成失败")

print()
print("请查看生成的标签文件，确认:")
print("1. 是否不显示参考配比区域")
print("2. 是否不显示搅拌提示文字")
print("3. 纵向分布是否更紧凑")
print("4. 底部空白是否减少")
