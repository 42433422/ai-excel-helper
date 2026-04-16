# -*- coding: utf-8 -*-
"""
使用 PaddleOCR 表格识别
"""

from paddleocr import PaddleOCR
import json
import glob

# 读取图片
files = glob.glob(r'e:\FHD\26-0300001A*.png')
image_path = files[0]
print(f"读取图片：{image_path}")

# 初始化 PaddleOCR
print("初始化 PaddleOCR...")
ocr = PaddleOCR(lang='ch', use_angle_cls=True)

print("执行表格 OCR...")
result = ocr.ocr(image_path, cls=True)

print(f"\n返回结果类型：{type(result)}")

if result is None or len(result) == 0:
    print("❌ 未检测到任何内容")
    exit(1)

print(f"\n" + "=" * 70)
print("OCR 结果")
print("=" * 70)

print(f"结果长度：{len(result)}")

for i, line in enumerate(result):
    print(f"\n--- 行 {i} ---")
    print(f"类型：{type(line)}")

    if isinstance(line, list):
        for j, item in enumerate(line):
            print(f"  [{j}]: {item}")

# 保存结果
output_path = r'e:\FHD\paddleocr_standard_result.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n✓ 结果已保存到：{output_path}")
