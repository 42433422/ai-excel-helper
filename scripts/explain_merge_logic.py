# -*- coding: utf-8 -*-
"""
详细解释合并检测逻辑
"""

import cv2
import numpy as np
import json
import glob

# 读取图片
files = glob.glob(r'e:\FHD\26-0300001A*.png')
image_path = files[0]

with open(image_path, 'rb') as f:
    file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
img_array = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

height, width = img_array.shape[:2]
gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
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
horizontal_lines = merge_lines(horizontal_lines, threshold=50)
vertical_lines = merge_lines(vertical_lines, threshold=50)

rows = len(horizontal_lines) - 1
cols = len(vertical_lines) - 1

print("=" * 70)
print("合并检测逻辑详解")
print("=" * 70)

print("\n【第一步：构建基础单元格】")
print(f"网格：{rows} 行 × {cols} 列")
print(f"水平线 Y：{horizontal_lines}")
print(f"垂直线 X：{vertical_lines}")

print("\n【第二步：检测边框缺失】")
print("对于每个单元格，检查其右侧边框的黑色像素占比：")

# 构建单元格并检测边框缺失
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
            'right_border_black_ratio': 0,
            'should_merge_with_next': False
        }

        # 检测右侧边框
        if j < cols - 1:
            right_border_x = x + w
            border_black_count = 0

            for check_y in range(y, y + h):
                if check_y < gray.shape[0] and right_border_x < gray.shape[1]:
                    if binary[check_y, right_border_x] > 0:
                        border_black_count += 1

            cell['right_border_black_ratio'] = border_black_count / h

            if border_black_count < h * 0.5:
                cell['should_merge_with_next'] = True

        cells.append(cell)

# 打印边框检测详情
for cell in cells:
    if cell['col'] < cols - 1:
        status = "✓ 合并" if cell['should_merge_with_next'] else "✗ 独立"
        print(f"  单元格[{cell['row']},{cell['col']}]: 右侧边框黑色占比 "
              f"{cell['right_border_black_ratio']*100:.1f}% → {status}")

print("\n【第三步：实际合并单元格】")
print("当单元格被标记为 'should_merge_with_next=True' 时，与右侧单元格合并：")
print("例如：单元格[0,1] should_merge_with_next=True，")
print("      则[0,1]和[0,2]合并成一个逻辑单元格\n")

# 构建合并后的逻辑单元格
merged_cells = []
visited = set()

for i in range(rows):
    for j in range(cols):
        cell_id = f"{i},{j}"
        if cell_id in visited:
            continue

        # 找到这个单元格
        cell = next(c for c in cells if c['row'] == i and c['col'] == j)

        # 计算这个单元格向右合并多少列
        merge_cols = 1
        while cell['should_merge_with_next'] and j + merge_cols < cols:
            visited.add(f"{i},{j + merge_cols}")
            merge_cols += 1
            if j + merge_cols < cols:
                next_cell = next((c for c in cells if c['row'] == i and c['col'] == j + merge_cols), None)
                if next_cell:
                    cell = next_cell
                else:
                    break

        # 计算合并后的实际位置和尺寸
        start_j = j
        end_j = j + merge_cols

        merged_x = vertical_lines[start_j]
        merged_y = horizontal_lines[i]
        merged_width = vertical_lines[end_j] - vertical_lines[start_j]
        merged_height = horizontal_lines[i + 1] - horizontal_lines[i]

        merged_cells.append({
            'row': i,
            'start_col': start_j,
            'end_col': end_j - 1,
            'merge_cols': merge_cols,
            'x': merged_x,
            'y': merged_y,
            'width': merged_width,
            'height': merged_height,
            'original_cells': list(range(start_j, end_j))
        })

        visited.add(cell_id)

print("【最终合并结果】")
for mc in merged_cells:
    if mc['merge_cols'] > 1:
        print(f"  逻辑单元格: 行{mc['row']}, 列{mc['start_col']}-{mc['end_col']} "
              f"(合并了 {mc['merge_cols']} 列)")
        print(f"    位置: ({mc['x']}, {mc['y']}) 尺寸: {mc['width']}×{mc['height']}")
        print(f"    包含的原始单元格: {mc['original_cells']}")
    else:
        print(f"  逻辑单元格: 行{mc['row']}, 列{mc['start_col']} (独立单元格)")

print(f"\n总结：{len(merged_cells)} 个逻辑单元格")
