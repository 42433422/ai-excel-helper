# -*- coding: utf-8 -*-
"""
使用 PaddleOCR PP-Structure 表格检测 + OCR
"""

from paddleocr import PPStructure
import cv2
import numpy as np
import json
import glob

# 读取图片
files = glob.glob(r'e:\FHD\26-0300001A*.png')
image_path = files[0]
print(f"读取图片：{image_path}")

# 初始化 PP-Structure（启用表格识别）
print("初始化 PP-Structure 表格引擎...")
structure_engine = PPStructure(table=True, ocr=True, show_log=False)

print("执行版面分析 + 表格 OCR 识别...")
result = structure_engine(image_path)

print(f"\n返回结果类型：{type(result)}")

if result is None or len(result) == 0:
    print("❌ 未检测到任何内容")
    exit(1)

print(f"\n" + "=" * 70)
print("PP-Structure 结果")
print("=" * 70)

for i, item in enumerate(result):
    print(f"\n--- 检测项 {i} ---")
    print(f"类型：{item.get('type', 'unknown')}")
    print(f"内容 keys：{item.keys()}")

    if 'table' in item:
        print(f"\n表格结构：")
        table_result = item['table']
        if isinstance(table_result, list):
            for row_idx, row in enumerate(table_result):
                print(f"  行 {row_idx}: {row}")

    if 'img' in item:
        print(f"\n检测到图片区域")

    if 'layout' in item:
        print(f"\n版面分析结果：{item['layout']}")

# 保存完整结果为 JSON
output_path = r'e:\FHD\paddleocr_result.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n✓ 结果已保存到：{output_path}")
