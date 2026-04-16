# -*- coding: utf-8 -*-
"""
使用 PaddleOCR predict 方法 - 处理中文路径
"""

from paddleocr import PaddleOCR
import numpy as np
import cv2
import json
import glob

# 读取图片
files = glob.glob(r'e:\FHD\26-0300001A*.png')
image_path = files[0]
print(f"读取图片：{image_path}")

# 用 cv2 读取图片（支持中文路径）
with open(image_path, 'rb') as f:
    file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
img_array = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

print(f"图片尺寸：{img_array.shape}")

# 初始化 PaddleOCR
print("初始化 PaddleOCR...")
ocr = PaddleOCR(lang='ch')

print("执行 OCR...")
result = ocr.predict(img_array)

print(f"\n返回结果类型：{type(result)}")

if result is None:
    print("❌ 未检测到任何内容")
    exit(1)

print(f"\n" + "=" * 70)
print("OCR 结果")
print("=" * 70)

# 获取结果
if hasattr(result, 'dt_polys'):
    print(f"检测到的文本框数量：{len(result.dt_polys)}")

if hasattr(result, 'rec_res'):
    print(f"识别结果数量：{len(result.rec_res)}")
    for i, (text, score) in enumerate(result.rec_res[:20]):  # 只显示前20个
        print(f"  [{i}]: {text} (置信度: {score:.2f})")

# 尝试获取表格结构
if hasattr(result, 'table'):
    print(f"\n表格结构：")
    print(result.table)
