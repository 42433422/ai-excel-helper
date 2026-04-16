# -*- coding: utf-8 -*-
"""
使用 PaddleOCR predict 方法 - 检查结果结构
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
print(f"结果长度：{len(result) if result else 0}")

if result and len(result) > 0:
    print(f"\n第一个结果的类型：{type(result[0])}")
    print(f"第一个结果：{result[0]}")

    # 检查结果的所有属性
    if hasattr(result[0], '__dict__'):
        print(f"\n结果的所有属性：")
        for attr in dir(result[0]):
            if not attr.startswith('_'):
                try:
                    value = getattr(result[0], attr)
                    if not callable(value):
                        print(f"  {attr}: {value}")
                except:
                    pass

    # 尝试不同的属性名
    print(f"\n尝试获取识别结果...")
    for attr in ['dt_polys', 'rec_res', 'text', ' texts', 'data', 'nec', 'table_html', 'table']:
        if hasattr(result[0], attr):
            print(f"  {attr}: {getattr(result[0], attr)}")
