# -*- coding: utf-8 -*-
"""
测试两个标签图片的表格识别 - 修正版
"""

from paddleocr import PaddleOCR
import numpy as np
import cv2
import json
import glob

def recognize_table(image_path):
    """识别表格"""
    print(f"\n读取图片：{image_path}")

    with open(image_path, 'rb') as f:
        file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
    img_array = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    height, width = img_array.shape[:2]
    print(f"图片尺寸：{width} x {height}")

    # OpenCV 网格线检测
    gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)

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

    print(f"网格线：{rows} 行 × {cols} 列")

    # PaddleOCR 文本检测
    ocr = PaddleOCR(lang='ch')
    result = ocr.predict(img_array)

    if not result or len(result) == 0:
        print("❌ OCR 未检测到内容")
        return None

    ocr_result = result[0]
    json_result = ocr_result.json
    res_data = json_result.get('res', {})

    rec_texts = res_data.get('rec_texts', [])
    rec_polys = res_data.get('rec_polys', [])

    print(f"检测到 {len(rec_texts)} 个文本框")

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
            'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
            'center_x': (x1 + x2) / 2,
            'center_y': (y1 + y2) / 2
        })

    def find_cell(x, y, h_lines, v_lines):
        row = 0
        for i in range(len(h_lines) - 1):
            if h_lines[i] <= y < h_lines[i + 1]:
                row = i
                break
        col = 0
        for j in range(len(v_lines) - 1):
            if v_lines[j] <= x < v_lines[j + 1]:
                col = j
                break
        return row, col

    cells = {}
    for row in range(rows):
        for col in range(cols):
            cells[(row, col)] = None

    for box in text_boxes:
        row, col = find_cell(box['center_x'], box['center_y'], horizontal_lines, vertical_lines)
        if 0 <= row < rows and 0 <= col < cols:
            if cells[(row, col)] is None:
                cells[(row, col)] = box

    merged_horizontal = []
    for row in range(rows):
        for col in range(cols - 1):
            if cells.get((row, col)) is not None and cells.get((row, col + 1)) is None:
                cell = cells[(row, col)]
                right_border_x = cell['x2']
                y_top = horizontal_lines[row]
                y_bottom = horizontal_lines[row + 1]

                border_black_count = 0
                for check_y in range(y_top, y_bottom):
                    if check_y < height and right_border_x < width:
                        if binary[check_y, right_border_x] > 0:
                            border_black_count += 1

                border_ratio = border_black_count / (y_bottom - y_top)

                if border_ratio < 0.5:
                    merged_horizontal.append({
                        'row': row,
                        'start_col': col,
                        'end_col': col + 1,
                        'cell': cell
                    })

    final_table = []
    for row in range(rows):
        row_data = {'Row': row, 'cells': []}
        col = 0
        while col < cols:
            cell_content = cells.get((row, col))

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
                    'is_merged': True
                })
                col = merged['end_col'] + 1
            elif cell_content:
                row_data['cells'].append({
                    'text': cell_content['text'],
                    'start_col': col,
                    'end_col': col,
                    'is_merged': False
                })
                col += 1
            else:
                col += 1

        final_table.append(row_data)

    return {
        'image_size': {'width': width, 'height': height},
        'grid': {'rows': rows, 'cols': cols},
        'horizontal_lines': horizontal_lines,
        'vertical_lines': vertical_lines,
        'merged_horizontal': [{'row': m['row'], 'start_col': m['start_col'], 'end_col': m['end_col']} for m in merged_horizontal],
        'table': final_table
    }

# 测试两个图片
images = [
    r'e:\FHD\26-0300001A_第1项_PE白底漆.png',
    r'e:\FHD\26-0300001A_第1项_PE封固底漆稀料.png'
]

results = {}
for img_path in images:
    print("\n" + "=" * 70)
    filename = img_path.split('\\')[-1]
    print(f"测试：{filename}")
    print("=" * 70)

    if not glob.glob(img_path):
        print(f"❌ 文件不存在：{img_path}")
        continue

    result = recognize_table(img_path)
    if result:
        name = filename.replace('.png', '')
        results[name] = result
        print(f"\n表格结构：")
        for row_data in result['table']:
            cells_str = []
            for cell in row_data['cells']:
                if cell['is_merged']:
                    cells_str.append(f"[{cell['start_col']}-{cell['end_col']}]{cell['text']}")
                else:
                    cells_str.append(f"[{cell['start_col']}]{cell['text']}")
            print(f"  行{row_data['Row']}: {' | '.join(cells_str)}")

output_path = r'e:\FHD\test_results.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n\n✓ 结果已保存到：{output_path}")
