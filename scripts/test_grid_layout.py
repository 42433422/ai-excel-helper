from paddleocr import PaddleOCR
from PIL import Image
import numpy as np
import glob
import cv2
import json

# 读取图片
png_files = glob.glob(r"E:\FHD\*PE*.png")
img_path = png_files[0]
img = Image.open(img_path)
img_array = np.array(img)
width, height = img.size

print(f"图片尺寸：{width} x {height}")
print("=" * 50)

# 1. 检测表格线
gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
edges = cv2.Canny(gray, 50, 150, apertureSize=3)

# 2. 检测水平线和垂直线
lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=50, maxLineGap=10)

horizontal_lines = []
vertical_lines = []

if lines is not None:
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if abs(y1 - y2) < 10:
            horizontal_lines.append(y1)
        elif abs(x1 - x2) < 10:
            vertical_lines.append(x1)

# 去重并排序
horizontal_lines = sorted(list(set([int(y) for y in horizontal_lines])))
vertical_lines = sorted(list(set([int(x) for x in vertical_lines])))

# 3. 合并相近的线条
def merge_close_lines(lines, threshold=30):
    if not lines:
        return []
    merged = [lines[0]]
    for line in lines[1:]:
        if line - merged[-1] > threshold:
            merged.append(line)
    return merged

horizontal_lines = merge_close_lines(horizontal_lines)
vertical_lines = merge_close_lines(vertical_lines)

print(f"\n=== 网格结构 ===")
print(f"水平线：{len(horizontal_lines)} 条 -> {horizontal_lines}")
print(f"垂直线：{len(vertical_lines)} 条 -> {vertical_lines}")

# 4. 根据网格线划分单元格
cells = []
if len(horizontal_lines) >= 2 and len(vertical_lines) >= 2:
    for i in range(len(horizontal_lines) - 1):
        for j in range(len(vertical_lines) - 1):
            cell = {
                'row': i,
                'col': j,
                'x1': vertical_lines[j],
                'y1': horizontal_lines[i],
                'x2': vertical_lines[j + 1],
                'y2': horizontal_lines[i + 1],
                'width': vertical_lines[j + 1] - vertical_lines[j],
                'height': horizontal_lines[i + 1] - horizontal_lines[i]
            }
            cells.append(cell)
    print(f"共 {len(cells)} 个单元格 ({len(horizontal_lines)-1}行 x {len(vertical_lines)-1}列)")

# 5. OCR 识别
print("\n=== OCR 识别 ===")
ocr = PaddleOCR(lang='ch')
result = ocr.predict(img_array)

# 处理返回结果
if isinstance(result, list) and len(result) > 0:
    result = result[0]

if isinstance(result, dict):
    rec_texts = result.get('rec_texts', [])
    rec_scores = result.get('rec_scores', [])
    rec_polys = result.get('rec_polys', [])
else:
    rec_texts = []
    rec_scores = []
    rec_polys = []

print(f"识别到 {len(rec_texts)} 个文本块\n")

# 6. 将文本映射到单元格
text_blocks = []
for i, text in enumerate(rec_texts):
    if i < len(rec_polys) and len(rec_polys[i]) > 0:
        bbox = rec_polys[i]
        center_x = sum([p[0] for p in bbox]) / len(bbox)
        center_y = sum([p[1] for p in bbox]) / len(bbox)
        score = rec_scores[i] if i < len(rec_scores) else 0
        
        # 查找文本所在的单元格
        cell_match = None
        for cell in cells:
            if (cell['x1'] <= center_x <= cell['x2'] and 
                cell['y1'] <= center_y <= cell['y2']):
                cell_match = cell
                break
        
        block = {
            'text': text,
            'confidence': score,
            'center': (center_x, center_y),
            'bbox': bbox,
            'cell': f"[{cell_match['row']},{cell_match['col']}]" if cell_match else "None",
            'row': cell_match['row'] if cell_match else -1,
            'col': cell_match['col'] if cell_match else -1,
            'y_center': center_y
        }
        text_blocks.append(block)
        
        if cell_match:
            print(f"'{text}' (置信度：{score:.2f}) -> 单元格 [{cell_match['row']},{cell_match['col']}] Y={center_y:.1f}")
        else:
            print(f"'{text}' (置信度：{score:.2f}) -> 未匹配单元格")

# 7. 智能字段配对（基于行和列位置）
print("\n=== 智能字段配对 ===")

# 按 Y 坐标排序文本块
text_blocks_sorted = sorted(text_blocks, key=lambda x: x['y_center'])

# 将文本块按 Y 坐标分组（同一行的文本）
def group_by_row(blocks, y_threshold=30):
    groups = []
    current_group = []
    current_y = None
    
    for block in blocks:
        if current_y is None or abs(block['y_center'] - current_y) <= y_threshold:
            current_group.append(block)
            current_y = block['y_center']
        else:
            groups.append(current_group)
            current_group = [block]
            current_y = block['y_center']
    
    if current_group:
        groups.append(current_group)
    
    return groups

row_groups = group_by_row(text_blocks_sorted, y_threshold=30)

print(f"\n按行分组：{len(row_groups)} 行\n")

fields = []
for i, group in enumerate(row_groups):
    print(f"行 {i}: {[b['text'] for b in group]}")
    
    # 同一行内，按 X 坐标排序（从左到右）
    group_sorted = sorted(group, key=lambda x: x['center'][0])
    
    # 配对：标签 + 值
    for j in range(0, len(group_sorted), 2):
        if j + 1 < len(group_sorted):
            label_block = group_sorted[j]
            value_block = group_sorted[j + 1]
            fields.append({
                'label': label_block['text'],
                'value': value_block['text'],
                'row_group': i,
                'confidence': (label_block['confidence'] + value_block['confidence']) / 2
            })
            print(f"  -> {label_block['text']}: {value_block['text']}")
        elif j < len(group_sorted):
            # 单独一个，可能是跨列的标签
            fields.append({
                'label': group_sorted[j]['text'],
                'value': '',
                'row_group': i,
                'confidence': group_sorted[j]['confidence']
            })
            print(f"  -> {group_sorted[j]['text']}: (空)")

print(f"\n共识别 {len(fields)} 个字段")

# 8. 输出网格配置
print("\n=== 网格配置 ===")
grid_config = {
    'image_size': {'width': width, 'height': height},
    'grid_size': {
        'rows': len(horizontal_lines) - 1,
        'cols': len(vertical_lines) - 1
    },
    'horizontal_lines': horizontal_lines,
    'vertical_lines': vertical_lines,
    'fields': fields
}
print(json.dumps(grid_config, indent=2, ensure_ascii=False))
