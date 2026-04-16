# -*- coding: utf-8 -*-
"""
使用 PaddleOCR 文本位置推断表格结构 - 修正版
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

# 获取 OCR 结果 - 从 json 属性获取
ocr_result = result[0]
print(f"\n结果类型：{type(ocr_result)}")

# 获取 JSON 格式的结果
json_result = ocr_result.json
print(f"JSON 结果 keys：{json_result.keys()}")

res_data = json_result.get('res', {})
print(f"res 数据 keys：{res_data.keys()}")

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

    # 计算边界框 [x1, y1, x2, y2]
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

# 根据 Y 坐标分行
print(f"\n" + "=" * 70)
print("根据 Y 坐标分行")
print("=" * 70)

# 提取所有 Y 坐标（用于确定行分隔）
y_coords = []
for box in text_boxes:
    y_coords.append(box['y1'])
    y_coords.append(box['y2'])

y_coords = sorted(set(y_coords))
print(f"Y 坐标点：{y_coords}")

# 计算行间距
y_diff = []
for i in range(len(y_coords) - 1):
    y_diff.append((y_coords[i+1] + y_coords[i]) / 2)

print(f"行分隔线 Y：{y_diff}")

# 分配行号
for box in text_boxes:
    row = 0
    for i, threshold in enumerate(y_diff):
        if box['center_y'] > threshold:
            row = i + 1
    box['row'] = row

# 根据 X 坐标分列
x_coords = []
for box in text_boxes:
    x_coords.append(box['x1'])
    x_coords.append(box['x2'])

x_coords = sorted(set(x_coords))
print(f"\nX 坐标点：{x_coords}")

# 计算列间距
x_diff = []
for i in range(len(x_coords) - 1):
    x_diff.append((x_coords[i+1] + x_coords[i]) / 2)

print(f"列分隔线 X：{x_diff}")

# 分配列号
for box in text_boxes:
    col = 0
    for i, threshold in enumerate(x_diff):
        if box['center_x'] > threshold:
            col = i + 1
    box['col'] = col

# 打印表格结构
print(f"\n" + "=" * 70)
print("推断的表格结构")
print("=" * 70)

# 按行分组
rows_data = {}
for box in text_boxes:
    row = box['row']
    col = box['col']
    if row not in rows_data:
        rows_data[row] = {}
    rows_data[row][col] = box['text']

# 打印表格
for row in sorted(rows_data.keys()):
    cols = rows_data[row]
    row_text = " | ".join([cols.get(c, '') for c in sorted(cols.keys())])
    print(f"行 {row}: {row_text}")

# 保存结果
output_data = {
    'image_size': {'width': img_array.shape[1], 'height': img_array.shape[0]},
    'text_boxes': text_boxes,
    'table_structure': rows_data,
    'y_separators': y_diff,
    'x_separators': x_diff
}

output_path = r'e:\FHD\ocr_table_structure.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(output_data, f, ensure_ascii=False, indent=2)

print(f"\n✓ 结果已保存到：{output_path}")
