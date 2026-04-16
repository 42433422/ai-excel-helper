# -*- coding: utf-8 -*-
"""
使用 PaddleOCR PPStructure 表格识别
"""

from paddleocr import PPStructure
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

# 初始化 PPStructure
print("初始化 PPStructure...")
table_engine = PPStructure(table=True, ocr=True, show_log=False)

print("执行表格结构识别...")
result = table_engine(img_array)

print(f"\n返回结果类型：{type(result)}")
print(f"结果长度：{len(result) if result else 0}")

if result and len(result) > 0:
    print(f"\n第一个结果的类型：{type(result[0])}")

    # 打印结果结构
    if isinstance(result[0], dict):
        print(f"结果 keys：{result[0].keys()}")

        if 'table' in result[0]:
            print(f"\n表格结构：")
            print(result[0]['table'])

        if 'img' in result[0]:
            print(f"\n检测到图片")

        if 'res' in result[0]:
            print(f"\nOCR 结果：")
            for i, item in enumerate(result[0]['res']):
                print(f"  {i}: {item}")

# 保存完整结果
output_path = r'e:\FHD\ppsructure_result.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2, default=str)

print(f"\n✓ 结果已保存到：{output_path}")
