# -*- coding: utf-8 -*-
"""
测试空白网格的网格检测逻辑
"""

import cv2
import numpy as np
from PIL import Image

# 读取空白网格图片
image_path = r'e:\FHD\blank_grid_template.png'
img = Image.open(image_path)
width, height = img.size

print(f"图片尺寸：{width} x {height}")
print("=" * 60)

# 转换为 OpenCV 格式
img_array = np.array(img)
gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

# 二值化：只检测非常黑的像素
_, binary = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)

# 检测水平线
horizontal_lines = []
for y in range(gray.shape[0]):
    row = binary[y, :]
    continuous_start = None
    max_continuous_length = 0
    current_length = 0
    
    for x in range(len(row)):
        if row[x] > 0:
            if continuous_start is None:
                continuous_start = x
            current_length += 1
        else:
            if current_length > max_continuous_length:
                max_continuous_length = current_length
            continuous_start = None
            current_length = 0
    
    if current_length > max_continuous_length:
        max_continuous_length = current_length
    
    if max_continuous_length > gray.shape[1] * 0.5:
        horizontal_lines.append(y)

# 检测垂直线
vertical_lines = []
for x in range(gray.shape[1]):
    col = binary[:, x]
    continuous_start = None
    max_continuous_length = 0
    current_length = 0
    
    for y in range(len(col)):
        if col[y] > 0:
            if continuous_start is None:
                continuous_start = y
            current_length += 1
        else:
            if current_length > max_continuous_length:
                max_continuous_length = current_length
            continuous_start = None
            current_length = 0
    
    if current_length > max_continuous_length:
        max_continuous_length = current_length
    
    if max_continuous_length > gray.shape[0] * 0.5:
        vertical_lines.append(x)

# 去重并排序
horizontal_lines = sorted(list(set([int(y) for y in horizontal_lines])))
vertical_lines = sorted(list(set([int(x) for x in vertical_lines])))

# 合并相近的线条
def merge_close_lines(lines, threshold=50):
    if not lines:
        return []
    merged = [lines[0]]
    for line in lines[1:]:
        if line - merged[-1] > threshold:
            merged.append(line)
    return merged

# 先合并粗边框导致的相邻线条（距离 < 5 像素的）
def merge_very_close_lines(lines, threshold=5):
    if not lines:
        return []
    merged = [lines[0]]
    for line in lines[1:]:
        if line - merged[-1] > threshold:
            merged.append(line)
        else:
            # 取中间值作为合并后的位置
            merged[-1] = (merged[-1] + line) // 2
    return merged

horizontal_lines = merge_very_close_lines(horizontal_lines, threshold=5)
vertical_lines = merge_very_close_lines(vertical_lines, threshold=5)

horizontal_lines_merged = merge_close_lines(horizontal_lines, threshold=50)
vertical_lines_merged = merge_close_lines(vertical_lines, threshold=50)

print(f"\n检测结果:")
print(f"  水平线：{len(horizontal_lines)} 条 -> 合并后：{len(horizontal_lines_merged)} 条")
print(f"  垂直线：{len(vertical_lines)} 条 -> 合并后：{len(vertical_lines_merged)} 条")

print(f"\n水平线 Y 坐标:")
for i, y in enumerate(horizontal_lines):
    marker = "✓" if y in horizontal_lines_merged else " "
    print(f"  {marker} [{i}] Y={y}")

print(f"\n垂直线 X 坐标:")
for i, x in enumerate(vertical_lines):
    marker = "✓" if x in vertical_lines_merged else " "
    print(f"  {marker} [{i}] X={x}")

print(f"\n合并后的坐标:")
print(f"  水平线：{horizontal_lines_merged}")
print(f"  垂直线：{vertical_lines_merged}")

print(f"\n网格结构:")
rows = len(horizontal_lines_merged) - 1 if len(horizontal_lines_merged) > 1 else 0
cols = len(vertical_lines_merged) - 1 if len(vertical_lines_merged) > 1 else 0
print(f"  {rows} 行 x {cols} 列 = {rows * cols} 个单元格")

print("=" * 60)
print("✓ 测试完成")
