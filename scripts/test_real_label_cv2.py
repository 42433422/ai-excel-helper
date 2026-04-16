# -*- coding: utf-8 -*-
"""
测试实际标签图片的网格检测 - 使用 Unicode 路径
"""

import cv2
import numpy as np
import os

# 使用 Unicode 路径
image_path = 'e:\\FHD\\26-0300001A_第 1 项_PE 封固底漆稀料.png'

print(f"正在读取图片：{image_path}")
print(f"文件存在：{os.path.exists(image_path)}")

# 使用 Unicode 路径读取
try:
    with open(image_path, 'rb') as f:
        file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
    img_array = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if img_array is None:
        print(f"❌ 解码失败")
        exit(1)
except Exception as e:
    print(f"❌ 读取失败：{e}")
    # 尝试使用 glob 找到的第一个文件
    import glob
    files = glob.glob(r'e:\FHD\26-0300001A*.png')
    if files:
        print(f"\n使用 glob 找到的文件：{files[0]}")
        image_path = files[0]
        with open(image_path, 'rb') as f:
            file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
        img_array = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    else:
        exit(1)

height, width = img_array.shape[:2]
print(f"图片尺寸：{width} x {height}")
print("=" * 60)

# 转换为灰度图
gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)

# 显示一些统计信息
print(f"\n图片统计:")
print(f"  最小值：{np.min(gray)}")
print(f"  最大值：{np.max(gray)}")
print(f"  平均值：{np.mean(gray):.2f}")

# 二值化：只检测非常黑的像素（表格边框）
threshold_val = 50
_, binary = cv2.threshold(gray, threshold_val, 255, cv2.THRESH_BINARY_INV)

print(f"\n二值化统计 (阈值={threshold_val}):")
print(f"  黑色像素数：{np.sum(binary > 0)}")
print(f"  黑色像素占比：{np.sum(binary > 0) / binary.size * 100:.2f}%")

# 检测水平线：扫描每一行，查找连续的黑色线段
horizontal_lines = []
for y in range(gray.shape[0]):
    row = binary[y, :]
    continuous_start = None
    max_continuous_length = 0
    current_length = 0
    
    for x in range(len(row)):
        if row[x] > 0:  # 黑色像素
            if continuous_start is None:
                continuous_start = x
            current_length += 1
        else:
            if current_length > max_continuous_length:
                max_continuous_length = current_length
            continuous_start = None
            current_length = 0
    
    # 检查最后一段
    if current_length > max_continuous_length:
        max_continuous_length = current_length
    
    # 如果最长连续线段超过图片宽度的 50%，认为是表格线
    if max_continuous_length > gray.shape[1] * 0.5:
        horizontal_lines.append(y)

# 检测垂直线：扫描每一列，查找连续的黑色线段
vertical_lines = []
for x in range(gray.shape[1]):
    col = binary[:, x]
    continuous_start = None
    max_continuous_length = 0
    current_length = 0
    
    for y in range(len(col)):
        if col[y] > 0:  # 黑色像素
            if continuous_start is None:
                continuous_start = y
            current_length += 1
        else:
            if current_length > max_continuous_length:
                max_continuous_length = current_length
            continuous_start = None
            current_length = 0
    
    # 检查最后一段
    if current_length > max_continuous_length:
        max_continuous_length = current_length
    
    # 如果最长连续线段超过图片高度的 50%，认为是表格线
    if max_continuous_length > gray.shape[0] * 0.5:
        vertical_lines.append(x)

# 去重并排序
horizontal_lines_raw = sorted(list(set([int(y) for y in horizontal_lines])))
vertical_lines_raw = sorted(list(set([int(x) for x in vertical_lines])))

print(f"\n原始检测:")
print(f"  水平线：{len(horizontal_lines_raw)} 条")
print(f"  垂直线：{len(vertical_lines_raw)} 条")

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

horizontal_lines = merge_very_close_lines(horizontal_lines_raw, threshold=5)
vertical_lines = merge_very_close_lines(vertical_lines_raw, threshold=5)

horizontal_lines_merged = merge_close_lines(horizontal_lines, threshold=50)
vertical_lines_merged = merge_close_lines(vertical_lines, threshold=50)

print(f"\n合并后:")
print(f"  水平线：{len(horizontal_lines_merged)} 条")
print(f"  垂直线：{len(vertical_lines_merged)} 条")

print(f"\n水平线 Y 坐标:")
for i, y in enumerate(horizontal_lines_merged):
    print(f"  [{i}] Y={y}")

print(f"\n垂直线 X 坐标:")
for i, x in enumerate(vertical_lines_merged):
    print(f"  [{i}] X={x}")

print(f"\n网格结构:")
rows = len(horizontal_lines_merged) - 1 if len(horizontal_lines_merged) > 1 else 0
cols = len(vertical_lines_merged) - 1 if len(vertical_lines_merged) > 1 else 0
print(f"  {rows} 行 x {cols} 列 = {rows * cols} 个单元格")

# 计算每个单元格的尺寸
print(f"\n单元格尺寸:")
if len(horizontal_lines_merged) > 1 and len(vertical_lines_merged) > 1:
    for i in range(rows):
        for j in range(cols):
            cell_height = horizontal_lines_merged[i+1] - horizontal_lines_merged[i]
            cell_width = vertical_lines_merged[j+1] - vertical_lines_merged[j]
            print(f"  单元格 [{i},{j}]: {cell_width} x {cell_height}")

print("=" * 60)
print("✓ 测试完成")
