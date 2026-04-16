# -*- coding: utf-8 -*-
"""
使用 PaddleOCR predict 方法
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
ocr = PaddleOCR(lang='ch')

print("执行 OCR...")
result = ocr.predict(image_path)

print(f"\n返回结果类型：{type(result)}")

if result is None:
    print("❌ 未检测到任何内容")
    exit(1)

print(f"\n" + "=" * 70)
print("OCR 结果")
print("=" * 70)

# 获取结果
if hasattr(result, 'nec'):
    print(f"NEC 结果：{result.nec}")

if hasattr(result, 'dt_polys'):
    print(f"检测到的文本框数量：{len(result.dt_polys)}")

if hasattr(result, 'rec_res'):
    print(f"识别结果数量：{len(result.rec_res)}")
    for i, (text, score) in enumerate(result.rec_res):
        print(f"  [{i}]: {text} (置信度: {score:.2f})")

# 尝试获取表格结构
if hasattr(result, 'table'):
    print(f"\n表格结构：")
    print(result.table)
