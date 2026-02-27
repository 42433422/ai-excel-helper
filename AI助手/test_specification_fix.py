#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试产品规格浮动范围修复
"""

import os
import sys
from label_generator import ProductLabelGenerator
from datetime import datetime
import uuid

# 设置基础目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 创建商标导出目录
LABELS_EXPORT_DIR = os.path.join(BASE_DIR, '商标导出')
os.makedirs(LABELS_EXPORT_DIR, exist_ok=True)
print(f"商标导出目录: {LABELS_EXPORT_DIR}")

# 测试生成标签
print(f"\n测试生成带有规格浮动范围的产品标签...")

# 模拟产品数据，包含不同的规格
products = [
    {
        'name': 'PE白底漆',
        'model_number': '9803',
        'quantity_kg': 280.0,
        'quantity_tins': 10,
        'tin_spec': 28.0,
        'unit_price': 9.0,
        'amount': 2520.0
    },
    {
        'name': 'PU清面漆',
        'model_number': '7225',
        'quantity_kg': 200.0,
        'quantity_tins': 10,
        'tin_spec': 20.0,
        'unit_price': 12.0,
        'amount': 2400.0
    }
]

# 生成当前日期
current_date = datetime.now().strftime('%Y.%m.%d')
print(f"当前日期: {current_date}")

# 为每个产品生成标签
generated_labels = []
for i, product in enumerate(products):
    print(f"\n处理产品 {i+1}/{len(products)}:")
    print(f"  产品名称: {product.get('name')}")
    print(f"  产品编号: {product.get('model_number')}")
    print(f"  产品规格: {product.get('tin_spec')}kg")
    
    # 处理规格值，去掉.0
    tin_spec = product.get('tin_spec', 10)
    try:
        if tin_spec.is_integer():
            tin_spec = int(tin_spec)
    except:
        pass
    
    # 准备产品数据，添加规格浮动范围
    product_data = {
        'product_number': product.get('model_number', '') or product.get('model', ''),
        'product_name': product.get('name', '') or product.get('product_name', ''),
        'ratio': '1:0.5-0.6:0.5-0.8',  # 默认配比
        'production_date': current_date,
        'shelf_life': '6个月',
        'specification': f"{tin_spec}±0.1KG",  # 添加浮动范围，去掉.0，使用大写KG
        'inspector': '合格'
    }
    
    print(f"  生成规格: {product_data.get('specification')}")
    
    # 验证必需字段
    if not product_data['product_number'] or not product_data['product_name']:
        print("  跳过: 产品编号或名称为空")
        continue
    
    # 生成唯一文件名
    filename = f"label_test_spec_{i+1}_{uuid.uuid4().hex}.png"
    output_path = os.path.join(LABELS_EXPORT_DIR, filename)
    
    print(f"  生成标签文件: {filename}")
    print(f"  保存路径: {output_path}")
    
    # 生成标签
    try:
        generator = ProductLabelGenerator()
        generator.generate_label(product_data, output_path)
        print(f"  ✅ 标签生成成功")
        
        # 生成访问URL
        image_url = f"/商标导出/{filename}"
        
        generated_labels.append({
            'product_name': product_data['product_name'],
            'model_number': product_data['product_number'],
            'specification': product_data['specification'],
            'filename': filename,
            'file_path': output_path,
            'image_url': image_url
        })
    except Exception as e:
        print(f"  ❌ 标签生成失败: {str(e)}")
        import traceback
        traceback.print_exc()

# 输出生成结果
print(f"\n=== 生成结果 ===")
print(f"成功生成 {len(generated_labels)} 个产品标签")

if generated_labels:
    print(f"\n生成的标签文件:")
    for label in generated_labels:
        print(f"  - {label['filename']}")
        print(f"    产品: {label['product_name']} ({label['model_number']})")
        print(f"    规格: {label['specification']}")
        print(f"    路径: {label['file_path']}")
        print(f"    URL: {label['image_url']}")
else:
    print("\n❌ 没有生成任何标签")

print(f"\n标签保存目录: {LABELS_EXPORT_DIR}")
print(f"目录中的文件: {os.listdir(LABELS_EXPORT_DIR)}")
