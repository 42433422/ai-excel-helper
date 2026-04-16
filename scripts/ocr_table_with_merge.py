# -*- coding: utf-8 -*-
"""
使用 PaddleOCR + 文本位置分析检测合并单元格
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

print(f"图片尺寸：{img_array.shape}")

# 初始化 PaddleOCR
ocr = PaddleOCR(lang='ch')
result = ocr.predict(img_array)

if not result or len(result) == 0:
    print("❌ 未检测到任何内容")
    exit(1)

ocr_result = result[0]
json_result = ocr_result.json
res_data = json_result.get('res', {})

rec_texts = res_data.get('rec_texts', [])
rec_polys = res_data.get('rec_polys', [])

print(f"\n检测到 {len(rec_texts)} 个文本框")

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

# 分行（使用聚类）
print("\n" + "=" * 70)
print("分行")
print("=" * 70)

y_centers = sorted(set([int(box['center_y']) for box in text_boxes]))
y_gaps = [(y_centers[i], y_centers[i+1], y_centers[i+1] - y_centers[i])
          for i in range(len(y_centers) - 1)]

row_threshold = 50
row_separators = []
for y1, y2, gap in y_gaps:
    if gap > row_threshold:
        row_separators.append((y1 + y2) / 2)

print(f"Y 中心点：{y_centers}")
print(f"行分隔线 Y：{row_separators}")

for box in text_boxes:
    row = 0
    for i, sep in enumerate(row_separators):
        if box['center_y'] > sep:
            row = i + 1
    box['row'] = row

# 分列（使用聚类）
print("\n" + "=" * 70)
print("分列")
print("=" * 70)

x_centers = sorted(set([int(box['center_x']) for box in text_boxes]))
x_gaps = [(x_centers[i], x_centers[i+1], x_centers[i+1] - x_centers[i])
          for i in range(len(x_centers) - 1)]

col_threshold = 50
col_separators = []
for x1, x2, gap in x_gaps:
    if gap > col_threshold:
        col_separators.append((x1 + x2) / 2)

print(f"X 中心点：{x_centers}")
print(f"列分隔线 X：{col_separators}")

for box in text_boxes:
    col = 0
    for i, sep in enumerate(col_separators):
        if box['center_x'] > sep:
            col = i + 1
    box['col'] = col

# 检测合并单元格
print("\n" + "=" * 70)
print("检测合并单元格")
print("=" * 70)

# 方法：比较文本框的宽度和它所在列的宽度
# 如果文本框宽度 > 列宽度，说明它可能跨越了多列

# 计算每列的宽度
col_widths = {}
for i, sep in enumerate(col_separators):
    if i == 0:
        col_widths[i] = sep
    else:
        col_widths[i] = sep - col_separators[i-1]
col_widths[len(col_separators)] = img_array.shape[1] - col_separators[-1]

print(f"列宽度：{col_widths}")

# 检查每个文本框是否跨越多列
merged_cells = []
for box in text_boxes:
    text = box['text']
    row = box['row']
    col = box['col']
    box_width = box['width']

    # 计算这个文本框所在的列范围
    # 根据文本框的 x1 和 x2，检查它跨越了多少列

    # 计算文本框左侧和右侧对应的列
    left_col = col
    right_col = col

    # 检查左侧是否延伸到更左边的列
    for c in range(col - 1, -1, -1):
        # 计算这一列的左边界
        if c == 0:
            col_left = 0
        else:
            col_left = col_separators[c-1]

        # 如果文本框的左边界小于这一列的左边界 + 一个小偏移，说明它跨越了这一列
        if box['x1'] < col_left + 30:  # 30px 容差
            left_col = c

    # 检查右侧是否延伸到更右边的列
    for c in range(col + 1, len(col_separators) + 1):
        if c == len(col_separators):
            col_right = img_array.shape[1]
        else:
            col_right = col_separators[c-1]

        if box['x2'] > col_right - 30:  # 30px 容差
            right_col = c

    merge_cols = right_col - left_col + 1

    if merge_cols > 1:
        merged_cells.append({
            'text': text,
            'row': row,
            'start_col': left_col,
            'end_col': right_col,
            'merge_cols': merge_cols,
            'x': box['x1'],
            'y': box['y1'],
            'width': box['x2'] - box['x1'],
            'height': box['y2'] - box['y1']
        })
        print(f"合并单元格: '{text}' 行{row} 列{left_col}-{right_col} (合并{merge_cols}列)")

# 构建最终表格结构
print("\n" + "=" * 70)
print("最终表格结构")
print("=" * 70)

rows_data = {}
for box in text_boxes:
    row = box['row']
    col = box['col']
    if row not in rows_data:
        rows_data[row] = {}
    rows_data[row][col] = box['text']

for row in sorted(rows_data.keys()):
    cols = rows_data[row]
    # 检查这一行是否有合并
    row_merges = [m for m in merged_cells if m['row'] == row]
    if row_merges:
        print(f"行 {row}:")
        for m in row_merges:
            print(f"  合并单元格: '{m['text']}' 跨列 {m['start_col']}-{m['end_col']}")
    else:
        row_text = " | ".join([cols.get(c, '') for c in sorted(cols.keys())])
        print(f"行 {row}: {row_text}")

# 保存结果
output_data = {
    'image_size': {'width': img_array.shape[1], 'height': img_array.shape[0]},
    'text_boxes': text_boxes,
    'table_structure': rows_data,
    'merged_cells': merged_cells,
    'row_separators': row_separators,
    'col_separators': col_separators
}

output_path = r'e:\FHD\ocr_table_with_merged.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(output_data, f, ensure_ascii=False, indent=2)

print(f"\n✓ 结果已保存到：{output_path}")
