#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成修正生产日期位置的无参考配比标签
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
    'product_number': 'HL-999',
    'product_name': 'PU固化剂',  # 包含"剂"，应该不显示参考配比
    'ratio': '1:0.5-0.6:0.5-0.8',
    'production_date': '2026.02.01',
    'shelf_life': '6个月',
    'specification': '60±0.1KG',
    'inspector': '合格'
}

print("=== 生成修正生产日期位置的无参考配比标签 ===")
print(f"产品名称: {test_data['product_name']}")
print(f"是否包含'剂'或'料': {'是' if any(kw in test_data['product_name'] for kw in ['剂', '料']) else '否'}")
print(f"修正内容: 生产日期回到原来位置，保质期在右边")

# 生成标签
generator = ProductLabelGenerator()
filename = f"corrected_position_{uuid.uuid4().hex[:8]}.png"
output_path = os.path.join(LABELS_EXPORT_DIR, filename)
generator.generate_label(test_data, output_path)

if os.path.exists(output_path):
    print(f"✅ 位置修正标签生成成功: {filename}")
    print(f"📁 文件位置: {output_path}")
    print()
    print("布局修正:")
    print("之前：生产日期位置被错误修改")
    print("现在：生产日期回到左上角，保质期在右上角")
    print()
    print("正确的区域分布:")
    print("1. 产品编号区域: 25-125px (100px)")
    print("2. 产品名称区域: 125-225px (100px)")
    print("3. 生产日期+保质期区域: 225-325px (100px)")
    print("   - 生产日期（左上角）")
    print("   - 保质期（右上角）")
    print("4. 规格+检验员区域: 325-425px (100px)")
    print("   - 规格（左下角）")
    print("   - 检验员（右下角）")
    print("5. 底部空白: 425-600px (175px)")
else:
    print(f"❌ 标签生成失败")

print()
print("请查看生成的标签文件，确认:")
print("1. 生产日期是否在左上角")
print("2. 保质期是否在生产日期右边")
print("3. 5个区域是否均匀分布")
print("4. 是否不显示参考配比区域")
