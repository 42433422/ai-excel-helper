# -*- coding: utf-8 -*-
"""
测试 PE白底漆 标签图片的网格检测
"""

import cv2
import numpy as np
import glob

# 读取 PE白底漆 图片
files = glob.glob(r'e:\FHD\26-0300001A_第1项_PE白底漆.png')
if not files:
    print("❌ 未找到 PE白底漆.png 文件")
    exit(1)

image_path = files[0]
print(f"读取图片：{image_path}")

with open(image_path, 'rb') as f:
    file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
img_array = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

height, width = img_array.shape[:2]
print(f"图片尺寸：{width} x {height}")
print(f"比例：{width/height:.2f}:1")

gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
_, binary = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)

black_pixels = np.sum(binary > 0)
print(f"黑色像素：{black_pixels} ({black_pixels / binary.size * 100:.2f}%)")

# 检测水平线
horizontal_lines = []
for y in range(gray.shape[0]):
    row = binary[y, :]
    max_continuous = 0
    current = 0
    for x in range(len(row)):
        if row[x] > 0:
            current += 1
        else:
            if current > max_continuous:
                max_continuous = current
            current = 0
    if current > max_continuous:
        max_continuous = current
    if max_continuous > gray.shape[1] * 0.5:
        horizontal_lines.append(y)

# 检测垂直线
vertical_lines = []
for x in range(gray.shape[1]):
    col = binary[:, x]
    max_continuous = 0
    current = 0
    for y in range(len(col)):
        if col[y] > 0:
            current += 1
        else:
            if current > max_continuous:
                max_continuous = current
            current = 0
    if current > max_continuous:
        max_continuous = current
    if max_continuous > gray.shape[0] * 0.5:
        vertical_lines.append(x)

# 合并线条
def merge_very_close(lines, threshold=5):
    if not lines:
        return []
    merged = [lines[0]]
    for line in lines[1:]:
        if line - merged[-1] > threshold:
            merged.append(line)
        else:
            merged[-1] = (merged[-1] + line) // 2
    return merged

def merge_lines(lines, threshold=50):
    if not lines:
        return []
    merged = [lines[0]]
    for line in lines[1:]:
        if line - merged[-1] > threshold:
            merged.append(line)
    return merged

horizontal_lines = sorted(list(set(horizontal_lines)))
vertical_lines = sorted(list(set(vertical_lines)))
horizontal_lines = merge_very_close(horizontal_lines, threshold=5)
vertical_lines = merge_very_close(vertical_lines, threshold=5)
horizontal_lines = merge_lines(horizontal_lines, threshold=50)
vertical_lines = merge_lines(vertical_lines, threshold=50)

print(f"\n" + "=" * 70)
print("网格线检测结果")
print("=" * 70)
print(f"水平线 Y：{horizontal_lines}")
print(f"垂直线 X：{vertical_lines}")

rows = len(horizontal_lines) - 1
cols = len(vertical_lines) - 1
print(f"基本网格：{rows} 行 × {cols} 列")

# 构建单元格并检测边框
cells = []
for i in range(rows):
    for j in range(cols):
        x = vertical_lines[j]
        y = horizontal_lines[i]
        w = vertical_lines[j + 1] - vertical_lines[j]
        h = horizontal_lines[i + 1] - horizontal_lines[i]

        cell = {
            'row': i,
            'col': j,
            'x': x,
            'y': y,
            'width': w,
            'height': h,
            'should_merge_right': False,
            'should_merge_down': False,
            'right_border_ratio': 0,
            'bottom_border_ratio': 0
        }

        # 检测右侧边框
        if j < cols - 1:
            right_border_x = x + w
            border_black_count = 0
            for check_y in range(y, y + h):
                if check_y < gray.shape[0] and right_border_x < gray.shape[1]:
                    if binary[check_y, right_border_x] > 0:
                        border_black_count += 1
            cell['right_border_ratio'] = border_black_count / h if h > 0 else 0
            if h > 0 and border_black_count < h * 0.5:
                cell['should_merge_right'] = True

        # 检测底部边框
        if i < rows - 1:
            bottom_border_y = y + h
            border_black_count = 0
            for check_x in range(x, x + w):
                if check_x < gray.shape[1] and bottom_border_y < gray.shape[0]:
                    if binary[bottom_border_y, check_x] > 0:
                        border_black_count += 1
            cell['bottom_border_ratio'] = border_black_count / w if w > 0 else 0
            if w > 0 and border_black_count < w * 0.5:
                cell['should_merge_down'] = True

        cells.append(cell)

print(f"\n" + "=" * 70)
print("单元格边框检测详情")
print("=" * 70)
print(f"{'单元格':<12} {'右侧边框':<12} {'底部边框':<12} {'状态'}")
print("-" * 60)

for cell in cells:
    right_info = f"{cell['right_border_ratio']*100:.1f}%"
    bottom_info = f"{cell['bottom_border_ratio']*100:.1f}%"

    status = []
    if cell['should_merge_right']:
        status.append("水平合并✓")
    if cell['should_merge_down']:
        status.append("垂直合并✓")
    status_str = ", ".join(status) if status else "独立"

    print(f"[{cell['row']},{cell['col']}]         {right_info:<12} {bottom_info:<12} {status_str}")

# 统计合并
h_merged = sum(1 for c in cells if c['should_merge_right'])
v_merged = sum(1 for c in cells if c['should_merge_down'])
print(f"\n合并统计：")
print(f"  水平合并：{h_merged} 个单元格")
print(f"  垂直合并：{v_merged} 个单元格")
