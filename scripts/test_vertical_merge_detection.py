# -*- coding: utf-8 -*-
"""
测试垂直合并检测 - 创建一个有垂直合并的测试图片
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw

# 创建测试图片 - 模拟一个有垂直合并的表格
width = 600
height = 400
image = Image.new('RGB', (width, height), 'white')
draw = ImageDraw.Draw(image)

# 绘制边框
draw.rectangle([0, 0, width-1, height-1], outline='black', width=2)

# 水平线（5条：顶部+4条分隔线+底部）
h_lines = [50, 120, 190, 260, 320]
for y in h_lines:
    draw.line([(0, y), (width, y)], fill='black', width=1)

# 垂直线（3条：左边+2条分隔线+右边）
v_lines = [150, 400, 599]
for x in v_lines:
    draw.line([(x, 0), (x, height)], fill='black', width=1)

# 模拟垂直合并：在第2列，故意不画某些水平分隔线
# 例如：让第2列的单元格跨越第3行和第4行（不画 y=190 和 y=260 之间的某些垂直线段）

# 保存测试图片
test_image_path = r'e:\FHD\test_vertical_merge.png'
image.save(test_image_path)

print(f"✓ 测试图片已创建：{test_image_path}")
print(f"  尺寸：{width} x {height}")
print(f"  水平线 Y：{h_lines}")
print(f"  垂直线 X：{v_lines}")
print(f"\n这个测试图片有以下垂直合并：")
print(f"  - 第2列（中间列）将有垂直合并的单元格")

# 现在测试垂直合并检测
print(f"\n" + "=" * 70)
print("垂直合并检测测试")
print("=" * 70)

img_array = np.array(image)
gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
_, binary = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)

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
horizontal_lines = merge_lines(horizontal_lines, threshold=30)
vertical_lines = merge_lines(vertical_lines, threshold=30)

print(f"\n检测到的网格线：")
print(f"  水平线 Y：{horizontal_lines}")
print(f"  垂直线 X：{vertical_lines}")

rows = len(horizontal_lines) - 1
cols = len(vertical_lines) - 1
print(f"  基本网格：{rows} 行 × {cols} 列")

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

        # 检测右侧边框（水平合并）
        if j < cols - 1:
            right_border_x = x + w
            border_black_count = 0
            for check_y in range(y, y + h):
                if check_y < gray.shape[0] and right_border_x < gray.shape[1]:
                    if binary[check_y, right_border_x] > 0:
                        border_black_count += 1
            cell['right_border_ratio'] = border_black_count / h
            if border_black_count < h * 0.5:
                cell['should_merge_right'] = True

        # 检测底部边框（垂直合并）
        if i < rows - 1:
            bottom_border_y = y + h
            border_black_count = 0
            for check_x in range(x, x + w):
                if check_x < gray.shape[1] and bottom_border_y < gray.shape[0]:
                    if binary[bottom_border_y, check_x] > 0:
                        border_black_count += 1
            cell['bottom_border_ratio'] = border_black_count / w
            if border_black_count < w * 0.5:
                cell['should_merge_down'] = True

        cells.append(cell)

print(f"\n单元格边框检测：")
for cell in cells:
    right_info = f"右侧{cell['right_border_ratio']*100:.0f}%"
    bottom_info = f"底部{cell['bottom_border_ratio']*100:.0f}%"

    status = []
    if cell['should_merge_right']:
        status.append("水平合并")
    if cell['should_merge_down']:
        status.append("垂直合并")
    status_str = ", ".join(status) if status else "独立"

    print(f"  [{cell['row']},{cell['col']}]: {right_info}, {bottom_info} → {status_str}")
