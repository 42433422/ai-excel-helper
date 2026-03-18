#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成最终优化版本的无参考配比标签
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
    'specification': '12±0.1KG',
    'inspector': '合格'
}

print("=== 生成最终优化版本的无参考配比标签 ===")
print(f"产品名称: {test_data['product_name']}")
print(f"是否包含'剂'或'料': {'是' if any(kw in test_data['product_name'] for kw in ['剂', '料']) else '否'}")
print(f"优化效果: 减少底部空白到5px，保持适度的紧凑感")

# 生成标签
generator = ProductLabelGenerator()
filename = f"final_optimized_{uuid.uuid4().hex[:8]}.png"
output_path = os.path.join(LABELS_EXPORT_DIR, filename)
generator.generate_label(test_data, output_path)

if os.path.exists(output_path):
    print(f"✅ 最终优化标签生成成功: {filename}")
    print(f"📁 文件位置: {output_path}")
else:
    print(f"❌ 标签生成失败")

print()
print("优化对比:")
print("最初：无配比标签有很多空白")
print("第一次优化：减少间距和高度")
print("第二次优化：进一步减少底部空白到5px")
print()
print("现在的效果应该:")
print("1. 不显示参考配比区域")
print("2. 不显示搅拌提示文字")
print("3. 适度的紧凑感")
print("4. 底部空白恰到好处（5px）")
