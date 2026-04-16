# -*- coding: utf-8 -*-
"""
使用 PaddleOCR + 正确的合并单元格检测
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

# 分行
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

# 分列
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

# 构建表格
print("\n" + "=" * 70)
print("表格结构")
print("=" * 70)

# 按行分组
table = {}
for box in text_boxes:
    row = box['row']
    col = box['col']
    if row not in table:
        table[row] = {}
    table[row][col] = box['text']

for row in sorted(table.keys()):
    cols = table[row]
    row_str = " | ".join([f"[{c}]{cols[c]}" for c in sorted(cols.keys())])
    print(f"行 {row}: {row_str}")

# 正确的合并检测方法
print("\n" + "=" * 70)
print("合并单元格检测")
print("=" * 70)

# 方法：比较文本框宽度和列宽度的比例
# 如果文本框宽度 > 该列宽度的 80%，说明它可能跨越了多列

# 计算每列的起始位置
col_boundaries = [0] + [sep for sep in col_separators] + [img_array.shape[1]]
col_widths = {}
for i in range(len(col_boundaries) - 1):
    col_widths[i] = col_boundaries[i+1] - col_boundaries[i]

print(f"列边界：{col_boundaries}")
print(f"列宽度：{col_widths}")

# 检测合并
merged_cells = []
for box in text_boxes:
    row = box['row']
    col = box['col']
    box_width = box['width']

    # 计算这个文本框所在的列范围
    col_start = col_boundaries[col]
    col_end = col_boundaries[col + 1] if col + 1 < len(col_boundaries) else img_array.shape[1]
    actual_col_width = col_end - col_start

    # 检查文本框是否延伸到相邻列
    # 如果文本框的左边界小于当前列的左边界 + 10px，说明它跨越了左边
    # 如果文本框的右边界大于当前列的右边界 - 10px，说明它跨越了右边

    left_col = col
    right_col = col

    # 检查能否向左扩展
    for c in range(col - 1, -1, -1):
        if box['x1'] < col_boundaries[c] + 20:  # 20px 容差
            left_col = c
        else:
            break

    # 检查能否向右扩展
    for c in range(col + 1, len(col_boundaries) - 1):
        if box['x2'] > col_boundaries[c + 1] - 20:  # 20px 容差
            right_col = c
        else:
            break

    merge_count = right_col - left_col + 1

    if merge_count > 1:
        merged_cells.append({
            'text': box['text'],
            'row': row,
            'start_col': left_col,
            'end_col': right_col,
            'merge_cols': merge_count,
            'x': box['x1'],
            'y': box['y1'],
            'width': box['width'],
            'height': box['height']
        })
        print(f"合并: '{box['text']}' 起始列{left_col}-结束列{right_col} (合并{murge_count}列)")

# 构建最终输出
print("\n" + "=" * 70)
print("最终输出")
print("=" * 70)

final_table = []
for row in sorted(table.keys()):
    row_data = {'row': row, 'cells': []}
    cols = table[row]

    for col in sorted(cols.keys()):
        # 检查这个单元格是否是合并单元格的一部分
        merged = None
        for mc in merged_cells:
            if mc['row'] == row and mc['start_col'] <= col <= mc['end_col']:
                merged = mc
                break

        if merged:
            # 检查是否是这个合并单元格的起始
            if col == merged['start_col']:
                row_data['cells'].append({
                    'text': merged['text'],
                    'col': col,
                    'start_col': merged['start_col'],
                    'end_col': merged['end_col'],
                    'is_merged': True,
                    'merge_cols': merged['merge_cols']
                })
        else:
            row_data['cells'].append({
                'text': cols[col],
                'col': col,
                'start_col': col,
                'end_col': col,
                'is_merged': False,
                'merge_cols': 1
            })

    final_table.append(row_data)

for row_data in final_table:
    print(f"\n行 {row_data['row']}:")
    for cell in row_data['cells']:
        if cell['is_merged']:
            print(f"  [{cell['col']}] '{cell['text']}' (合并列{cell['start_col']}-{cell['end_col']})")
        else:
            print(f"  [{cell['col']}] '{cell['text']}'")

# 保存结果
output_data = {
    'image_size': {'width': img_array.shape[1], 'height': img_array.shape[0]},
    'text_boxes': text_boxes,
    'table': final_table,
    'merged_cells': merged_cells,
    'row_separators': row_separators,
    'col_separators': col_separators,
    'col_widths': col_widths
}

output_path = r'e:\FHD\ocr_table_final.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(output_data, f, ensure_ascii=False, indent=2)

print(f"\n✓ 结果已保存到：{output_path}")
