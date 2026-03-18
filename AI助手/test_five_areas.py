#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成5个区域均匀分布的无参考配比标签
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
    'product_number': 'HL-100',
    'product_name': 'PU固化剂',  # 包含"剂"，应该不显示参考配比
    'ratio': '1:0.5-0.6:0.5-0.8',
    'production_date': '2026.02.01',
    'shelf_life': '6个月',
    'specification': '50±0.1KG',
    'inspector': '合格'
}

print("=== 生成5个区域均匀分布的无参考配比标签 ===")
print(f"产品名称: {test_data['product_name']}")
print(f"是否包含'剂'或'料': {'是' if any(kw in test_data['product_name'] for kw in ['剂', '料']) else '否'}")
print(f"布局改进: 5个区域均匀分布，每个区域100px，底部留75px空白")

# 生成标签
generator = ProductLabelGenerator()
filename = f"five_equal_areas_{uuid.uuid4().hex[:8]}.png"
output_path = os.path.join(LABELS_EXPORT_DIR, filename)
generator.generate_label(test_data, output_path)

if os.path.exists(output_path):
    print(f"✅ 5个区域均匀分布标签生成成功: {filename}")
    print(f"📁 文件位置: {output_path}")
    print()
    print("布局改进:")
    print("之前：区域大小不协调，规格+检验员区域过大")
    print("现在：5个区域均匀分布，每个区域100px")
    print()
    print("新的区域分布:")
    print("1. 产品编号区域: 25-125px (100px)")
    print("2. 产品名称区域: 125-225px (100px)")
    print("3. 生产日期区域: 225-325px (100px)")
    print("4. 保质期区域: 325-425px (100px)")
    print("5. 规格+检验员区域: 425-525px (100px)")
    print("6. 底部空白: 525-600px (75px)")
    print()
    print("分割线改进:")
    print("✅ 保质期前面的垂直分割线")
    print("✅ 所有垂直分割线延伸到标签底部")
    print("✅ 水平分割线为每个区域添加边界")
else:
    print(f"❌ 标签生成失败")

print()
print("请查看生成的标签文件，确认:")
print("1. 5个区域是否均匀分布")
print("2. 布局是否更加协调")
print("3. 是否不显示参考配比区域")
print("4. 是否不显示搅拌提示文字")
