# -*- coding: utf-8 -*-
"""
使用 PaddleOCR 文本位置推断表格结构 - 改进版
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

# 用 cv2 读取图片
with open(image_path, 'rb') as f:
    file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
img_array = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

print(f"图片尺寸：{img_array.shape}")

# 初始化 PaddleOCR
print("初始化 PaddleOCR...")
ocr = PaddleOCR(lang='ch')

print("执行 OCR...")
result = ocr.predict(img_array)

if not result or len(result) == 0:
    print("❌ 未检测到任何内容")
    exit(1)

# 获取 OCR 结果
ocr_result = result[0]
json_result = ocr_result.json
res_data = json_result.get('res', {})

rec_texts = res_data.get('rec_texts', [])
rec_polys = res_data.get('rec_polys', [])
rec_scores = res_data.get('rec_scores', [])

print(f"\n检测到 {len(rec_texts)} 个文本框")

# 提取文本框信息
text_boxes = []
for i in range(len(rec_polys)):
    text = rec_texts[i]
    score = rec_scores[i]
    box = np.array(rec_polys[i])

    x1 = int(min(box[:, 0]))
    y1 = int(min(box[:, 1]))
    x2 = int(max(box[:, 0]))
    y2 = int(max(box[:, 1]))

    text_boxes.append({
        'text': text,
        'score': float(score),
        'x1': x1,
        'y1': y1,
        'x2': x2,
        'y2': y2,
        'center_x': (x1 + x2) / 2,
        'center_y': (y1 + y2) / 2
    })

print(f"\n" + "=" * 70)
print("OCR 识别结果")
print("=" * 70)
for i, box in enumerate(text_boxes):
    print(f"[{i:2d}] {box['text']:<15} 位置:({box['x1']:3d},{box['y1']:3d})-({box['x2']:3d},{box['y2']:3d})")

# 改进：使用聚类来分行
print(f"\n" + "=" * 70)
print("使用聚类算法分行")
print("=" * 70)

# 提取所有文本框的中心 Y 坐标
y_centers = [box['center_y'] for box in text_boxes]
y_centers = sorted(set([int(y) for y in y_centers]))

print(f"Y 中心坐标：{y_centers}")

# 计算相邻 Y 坐标的差距
y_gaps = []
for i in range(len(y_centers) - 1):
    gap = y_centers[i+1] - y_centers[i]
    y_gaps.append((y_centers[i], y_centers[i+1], gap))

print(f"Y 间隔：{[(y_gaps[i][0], y_gaps[i][1], f'{y_gaps[i][2]:.0f}px') for i in range(len(y_gaps))]}")

# 找到大的间隔作为行分隔
# 设定一个阈值：如果间隔 > 50px，则认为是行分隔
row_threshold = 50
row_separators = []
for i, (y1, y2, gap) in enumerate(y_gaps):
    if gap > row_threshold:
        row_separators.append((y1 + y2) / 2)

print(f"\n行分隔线 Y：{row_separators}")

# 分配行号
for box in text_boxes:
    row = 0
    for i, sep in enumerate(row_separators):
        if box['center_y'] > sep:
            row = i + 1
    box['row'] = row

# 同样的方法分列
x_centers = [box['center_x'] for box in text_boxes]
x_centers = sorted(set([int(x) for x in x_centers]))

x_gaps = []
for i in range(len(x_centers) - 1):
    gap = x_centers[i+1] - x_centers[i]
    x_gaps.append((x_centers[i], x_centers[i+1], gap))

print(f"\nX 间隔：{[(x_gaps[i][0], x_gaps[i][1], f'{x_gaps[i][2]:.0f}px') for i in range(len(x_gaps))]}")

col_threshold = 50
col_separators = []
for i, (x1, x2, gap) in enumerate(x_gaps):
    if gap > col_threshold:
        col_separators.append((x1 + x2) / 2)

print(f"\n列分隔线 X：{col_separators}")

# 分配列号
for box in text_boxes:
    col = 0
    for i, sep in enumerate(col_separators):
        if box['center_x'] > sep:
            col = i + 1
    box['col'] = col

# 打印表格结构
print(f"\n" + "=" * 70)
print("推断的表格结构")
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
    row_text = " | ".join([cols.get(c, '') for c in sorted(cols.keys())])
    print(f"行 {row}: {row_text}")

# 生成合并信息
print(f"\n" + "=" * 70)
print("合并单元格检测")
print("=" * 70)

# 检查是否有同一行内相邻列的文本应该合并
merged_cells = []
for row in sorted(rows_data.keys()):
    cols = rows_data[row]
    sorted_cols = sorted(cols.keys())

    # 找到连续的空列
    prev_col = -1
    for col in sorted_cols:
        if col > prev_col + 1:
            # 有空列，说明可能有合并
            pass
        prev_col = col

# 检测哪些单元格应该合并
for box in text_boxes:
    row = box['row']
    col = box['col']
    text = box['text']

    # 检查右侧是否有紧邻的单元格
    next_col = col + 1
    if next_col in rows_data[row]:
        next_text = rows_data[row][next_col]
        # 如果右侧文本紧贴着（间隔 < 50px），可能需要合并
        pass

# 保存结果
output_data = {
    'image_size': {'width': img_array.shape[1], 'height': img_array.shape[0]},
    'text_boxes': text_boxes,
    'table_structure': rows_data,
    'row_separators': row_separators,
    'col_separators': col_separators
}

output_path = r'e:\FHD\ocr_table_structure.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(output_data, f, ensure_ascii=False, indent=2)

print(f"\n✓ 结果已保存到：{output_path}")
