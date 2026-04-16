# -*- coding: utf-8 -*-
"""
使用 PaddleOCR 表格检测 + OCR
"""

from paddleocr import PaddleOCR
import cv2
import numpy as np
import json
import glob

# 读取图片
files = glob.glob(r'e:\FHD\26-0300001A*.png')
image_path = files[0]
print(f"读取图片：{image_path}")

# 初始化 PaddleOCR（启用表格引擎）
print("初始化 PaddleOCR 表格引擎...")
ocr = PaddleOCR(lang='ch', use_angle_cls=True, table_engine=True, show_log=False)

print("执行表格 OCR 识别...")
result = ocr.ocr(image_path, cls=True)

print(f"\n返回结果类型：{type(result)}")

if result is None:
    print("❌ 未检测到任何内容")
    exit(1)

# 分析结果
print(f"\n" + "=" * 70)
print("OCR + 表格检测结果")
print("=" * 70)

if isinstance(result, list):
    print(f"结果数量：{len(result)}")

    for i, item in enumerate(result):
        print(f"\n--- 结果项 {i} ---")
        print(f"类型：{type(item)}")

        if isinstance(item, (list, tuple)):
            print(f"内容：{item}")

        # 如果是表格结果
        if isinstance(item, dict):
            print(f"包含 keys：{item.keys()}")

            if 'table' in item:
                print(f"\n表格结果：")
                table_result = item['table']
                print(f"  类型：{type(table_result)}")

                if isinstance(table_result, list):
                    for j, row in enumerate(table_result):
                        print(f"  行 {j}: {row}")

            if 'res' in item:
                print(f"\nOCR 文本结果：")
                res = item['res']
                if isinstance(res, list):
                    for j, text in enumerate(res):
                        print(f"  {j}: {text}")

elif isinstance(result, dict):
    print(f"结果 keys：{result.keys()}")

    if 'table' in result:
        print(f"\n表格结果：")
        table_result = result['table']
        if isinstance(table_result, list):
            for j, row in enumerate(table_result):
                print(f"  行 {j}: {row}")

else:
    print(f"结果内容：{result}")
