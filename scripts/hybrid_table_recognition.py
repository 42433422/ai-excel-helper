# -*- coding: utf-8 -*-
"""
PaddleOCR 文本 + OpenCV 网格线 = 准确的表格结构
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

with open(image_path, 'rb') as f:
    file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
img_array = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

height, width = img_array.shape[:2]
print(f"图片尺寸：{width} x {height}")

# ============ 第一步：OpenCV 网格线检测 ============
print("\n" + "=" * 70)
print("第一步：OpenCV 网格线检测")
print("=" * 70)

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

print(f"水平线 Y：{horizontal_lines}")
print(f"垂直线 X：{vertical_lines}")

rows = len(horizontal_lines) - 1
cols = len(vertical_lines) - 1
print(f"网格：{rows} 行 × {cols} 列")

# ============ 第二步：PaddleOCR 文本检测 ============
print("\n" + "=" * 70)
print("第二步：PaddleOCR 文本检测")
print("=" * 70)

ocr = PaddleOCR(lang='ch')
result = ocr.predict(img_array)

if not result or len(result) == 0:
    print("❌ OCR 未检测到内容")
    exit(1)

ocr_result = result[0]
json_result = ocr_result.json
res_data = json_result.get('res', {})

rec_texts = res_data.get('rec_texts', [])
rec_polys = res_data.get('rec_polys', [])

print(f"检测到 {len(rec_texts)} 个文本框")

# 提取文本框信息
text_boxes = []
for i in range(len(rec_polys)):
    text = rec_texts[i]
    box = np.array(rec_polys[i])

    x1 = int(min(box[:, 0]))
    y1 = int(min(box[:, 1]))
    x2 = int(max(box[:, 0]))
    y2 = int(max(box[:, 1]))

    text_boxes.append({
        'text': text,
        'x1': x1,
        'y1': y1,
        'x2': x2,
        'y2': y2,
        'width': x2 - x1,
        'height': y2 - y1,
        'center_x': (x1 + x2) / 2,
        'center_y': (y1 + y2) / 2
    })

# ============ 第三步：文本框分配到单元格 ============
print("\n" + "=" * 70)
print("第三步：文本框分配到单元格")
print("=" * 70)

# 根据网格线将文本框分配到单元格
def find_cell(x, y, horizontal_lines, vertical_lines):
    """根据坐标找到单元格索引"""
    row = 0
    for i in range(len(horizontal_lines) - 1):
        if horizontal_lines[i] <= y < horizontal_lines[i + 1]:
            row = i
            break

    col = 0
    for j in range(len(vertical_lines) - 1):
        if vertical_lines[j] <= x < vertical_lines[j + 1]:
            col = j
            break

    return row, col

# 分配每个文本框到单元格
for box in text_boxes:
    row, col = find_cell(box['center_x'], box['center_y'], horizontal_lines, vertical_lines)
    box['cell_row'] = row
    box['cell_col'] = col

# 构建单元格内容
cells = {}
for row in range(rows):
    for col in range(cols):
        cells[(row, col)] = None

for box in text_boxes:
    row = box['cell_row']
    col = box['cell_col']
    if 0 <= row < rows and 0 <= col < cols:
        if cells[(row, col)] is None:
            cells[(row, col)] = box
        else:
            # 如果单元格已经有文本，说明可能跨单元格
            existing = cells[(row, col)]
            print(f"警告：单元格[{row},{col}]有多个文本：'{existing['text']}' 和 '{box['text']}'")

# 打印表格
print("\n表格内容：")
print("-" * 60)
for row in range(rows):
    row_texts = []
    for col in range(cols):
        cell = cells.get((row, col))
        if cell:
            row_texts.append(f"[{row},{col}]{cell['text']}")
        else:
            row_texts.append(f"[{row},{col}]-")
    print(" | ".join(row_texts))

# ============ 第四步：检测合并单元格 ============
print("\n" + "=" * 70)
print("第四步：检测合并单元格")
print("=" * 70)

# 检测水平合并：检查每个单元格的右侧边框
merged_horizontal = []
for row in range(rows):
    for col in range(cols - 1):
        if cells.get((row, col)) is not None and cells.get((row, col + 1)) is None:
            # 单元格[row,col]有内容，但右侧单元格[row,col+1]为空
            # 检查单元格[row,col]的右侧边框是否有线条
            cell = cells[(row, col)]
            right_border_x = cell['x2']
            y_top = horizontal_lines[row]
            y_bottom = horizontal_lines[row + 1]

            # 检查边框上是否有黑色像素
            border_black_count = 0
            for check_y in range(y_top, y_bottom):
                if check_y < height and right_border_x < width:
                    if binary[check_y, right_border_x] > 0:
                        border_black_count += 1

            border_ratio = border_black_count / (y_bottom - y_top)
            print(f"单元格[{row},{col}] '{cell['text']}' 右侧边框黑色占比：{border_ratio*100:.1f}%")

            if border_ratio < 0.5:
                merged_horizontal.append({
                    'row': row,
                    'start_col': col,
                    'end_col': col + 1,
                    'cell': cell
                })
                print(f"  → 水平合并！列{col}和列{col+1}合并")

# ============ 第五步：生成最终结果 ============
print("\n" + "=" * 70)
print("第五步：生成最终结果")
print("=" * 70)

final_table = []
for row in range(rows):
    row_data = {'row': row, 'cells': []}
    col = 0
    while col < cols:
        cell_content = cells.get((row, col))

        # 检查是否是合并单元格的起始
        merged = None
        for m in merged_horizontal:
            if m['row'] == row and m['start_col'] == col:
                merged = m
                break

        if merged:
            row_data['cells'].append({
                'text': merged['cell']['text'],
                'start_col': merged['start_col'],
                'end_col': merged['end_col'],
                'is_merged': True,
                'merge_cols': merged['end_col'] - merged['start_col'] + 1
            })
            col = merged['end_col'] + 1
        elif cell_content:
            row_data['cells'].append({
                'text': cell_content['text'],
                'start_col': col,
                'end_col': col,
                'is_merged': False,
                'merge_cols': 1
            })
            col += 1
        else:
            row_data['cells'].append({
                'text': '',
                'start_col': col,
                'end_col': col,
                'is_merged': False,
                'merge_cols': 1
            })
            col += 1

    final_table.append(row_data)

print("最终表格结构：")
for row_data in final_table:
    print(f"\n行 {row_data['row']}:")
    for cell in row_data['cells']:
        if cell['is_merged']:
            print(f"  [{cell['start_col']}-{cell['end_col']}] '{cell['text']}' (合并{cell['merge_cols']}列)")
        else:
            print(f"  [{cell['start_col']}] '{cell['text']}'")

# 保存结果
output_data = {
    'image_size': {'width': width, 'height': height},
    'horizontal_lines': horizontal_lines,
    'vertical_lines': vertical_lines,
    'grid': {'rows': rows, 'cols': cols},
    'text_boxes': text_boxes,
    'merged_horizontal': merged_horizontal,
    'table': final_table
}

output_path = r'e:\FHD\final_table_result.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(output_data, f, ensure_ascii=False, indent=2)

print(f"\n✓ 结果已保存到：{output_path}")
