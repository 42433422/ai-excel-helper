# -*- coding: utf-8 -*-
"""
测试修复后的合并单元格检测
"""

import cv2
import numpy as np
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

print(f"\n网格线：")
print(f"  水平线：{horizontal_lines}")
print(f"  垂直线：{vertical_lines}")

# 构建单元格并检测合并
rows = len(horizontal_lines) - 1
cols = len(vertical_lines) - 1

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
            'is_merged_horizontally': False,
            'is_merged_vertically': False
        }
        cells.append(cell)

# 检测水平合并：检查单元格右侧边框是否有黑色线段
for cell in cells:
    if cell['col'] < cols - 1:  # 不是最后一列
        right_border_x = cell['x'] + cell['width']
        border_black_count = 0

        # 统计右侧边框上有多少黑色像素
        for check_y in range(cell['y'], cell['y'] + cell['height']):
            if check_y < gray.shape[0] and right_border_x < gray.shape[1]:
                if binary[check_y, right_border_x] > 0:
                    border_black_count += 1

        print(f"\n单元格[{cell['row']},{cell['col']}] 右侧边框检查:")
        print(f"  边框位置: X={right_border_x}, Y范围=[{cell['y']}, {cell['y'] + cell['height']}]")
        print(f"  边框总高度: {cell['height']}")
        print(f"  黑色像素数: {border_black_count}")
        print(f"  占比: {border_black_count / cell['height'] * 100:.1f}%")

        # 如果右侧边框少于 50% 是黑色，认为是水平合并（边框缺失）
        if border_black_count < cell['height'] * 0.5:
            cell['is_merged_horizontally'] = True
            print(f"  → 判定为水平合并！")

# 检测垂直合并
for cell in cells:
    if cell['row'] < rows - 1:  # 不是最后一行
        bottom_border_y = cell['y'] + cell['height']
        border_black_count = 0

        for check_x in range(cell['x'], cell['x'] + cell['width']):
            if check_x < gray.shape[1] and bottom_border_y < gray.shape[0]:
                if binary[bottom_border_y, check_x] > 0:
                    border_black_count += 1

        # 如果底部边框少于 50% 是黑色，认为是垂直合并
        if border_black_count < cell['width'] * 0.5:
            cell['is_merged_vertically'] = True

print(f"\n" + "=" * 70)
print("单元格分析结果")
print("=" * 70)

for i, cell in enumerate(cells):
    status = []
    if cell['is_merged_horizontally']:
        status.append("水平合并")
    if cell['is_merged_vertically']:
        status.append("垂直合并")
    status_str = ", ".join(status) if status else "正常"

    print(f"[{i:2d}] 行{cell['row']} 列{cell['col']}: "
          f"({cell['x']:3d},{cell['y']:3d}) {cell['width']:3d}x{cell['height']:3d} [{status_str}]")

# 生成可视化 HTML
html_content = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>合并单元格检测结果</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        h1 {{ text-align: center; color: #333; }}
        .info {{ text-align: center; color: #666; margin-bottom: 20px; }}
        .preview {{ display: flex; gap: 20px; }}
        .canvas-wrapper {{ background: #fafafa; padding: 20px; border-radius: 4px; }}
        canvas {{ border: 2px solid #333; }}
        .cell-info {{ flex: 1; background: #f8f9fa; padding: 20px; border-radius: 4px; }}
        .cell {{ padding: 10px; margin: 5px 0; background: white; border-radius: 4px; border-left: 4px solid #007bff; }}
        .cell.merged-h {{ background: #fff3cd; border-left-color: #ffc107; }}
        .cell.merged-v {{ background: #d4edda; border-left-color: #28a745; }}
        .cell-num {{ font-weight: bold; }}
        .legend {{ display: flex; gap: 20px; margin-top: 20px; justify-content: center; }}
        .legend-item {{ display: flex; align-items: center; gap: 8px; }}
        .legend-color {{ width: 20px; height: 20px; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📋 合并单元格检测结果</h1>
        <div class="info">图片尺寸：{width} × {height} | 网格：{rows} 行 × {cols} 列</div>

        <div class="preview">
            <div class="canvas-wrapper">
                <canvas id="canvas" width="{width}" height="{height}"></canvas>
            </div>
            <div class="cell-info">
                <h3>单元格列表</h3>
'''

for cell in cells:
    status_class = ""
    if cell['is_merged_horizontally'] and cell['is_merged_vertically']:
        status_class = "merged-both"
    elif cell['is_merged_horizontally']:
        status_class = "merged-h"
    elif cell['is_merged_vertically']:
        status_class = "merged-v"

    status_text = []
    if cell['is_merged_horizontally']:
        status_text.append("水平合并")
    if cell['is_merged_vertically']:
        status_text.append("垂直合并")
    status_str = "正常" if not status_text else ", ".join(status_text)

    html_content += f'''                <div class="cell {status_class}">
                    <div class="cell-num">#[{cell['row']},{cell['col']}] {status_str}</div>
                    <div>位置: ({cell['x']}, {cell['y']}) 尺寸: {cell['width']}×{cell['height']}</div>
                </div>
'''

html_content += '''            </div>
        </div>

        <div class="legend">
            <div class="legend-item">
                <div class="legend-color" style="background: rgba(0,123,255,0.2); border: 2px solid #007bff;"></div>
                <span>正常</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: rgba(255,193,7,0.3); border: 2px solid #ffc107;"></div>
                <span>水平合并</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: rgba(40,167,69,0.3); border: 2px solid #28a745;"></div>
                <span>垂直合并</span>
            </div>
        </div>
    </div>

    <script>
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');

        const cells = ''' + json.dumps(cells) + ''';
        const horizontalLines = ''' + json.dumps(horizontal_lines) + ''';
        const verticalLines = ''' + json.dumps(vertical_lines) + ''';

        function draw() {
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            // 绘制单元格
            cells.forEach((cell, index) => {
                let fillColor = 'rgba(0, 123, 255, 0.2)';
                let borderColor = '#007bff';

                if (cell.is_merged_horizontally && cell.is_merged_vertically) {
                    fillColor = 'rgba(220, 53, 69, 0.2)';
                    borderColor = '#dc3545';
                } else if (cell.is_merged_horizontally) {
                    fillColor = 'rgba(255, 193, 7, 0.3)';
                    borderColor = '#ffc107';
                } else if (cell.is_merged_vertically) {
                    fillColor = 'rgba(40, 167, 69, 0.3)';
                    borderColor = '#28a745';
                }

                ctx.fillStyle = fillColor;
                ctx.fillRect(cell.x, cell.y, cell.width, cell.height);

                ctx.strokeStyle = borderColor;
                ctx.lineWidth = 2;
                ctx.strokeRect(cell.x, cell.y, cell.width, cell.height);

                ctx.fillStyle = '#333';
                ctx.font = 'bold 14px Arial';
                ctx.fillText(index, cell.x + 5, cell.y + 20);
            });

            // 绘制网格线
            ctx.strokeStyle = '#000';
            ctx.lineWidth = 1;

            horizontalLines.forEach(y => {
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(canvas.width, y);
                ctx.stroke();
            });

            verticalLines.forEach(x => {
                ctx.beginPath();
                ctx.moveTo(x, 0);
                ctx.lineTo(x, canvas.height);
                ctx.stroke();
            });

            // 边框
            ctx.strokeStyle = '#000';
            ctx.lineWidth = 3;
            ctx.strokeRect(0, 0, canvas.width, canvas.height);
        }

        draw();
    </script>
</body>
</html>
'''

output_path = r'e:\FHD\merged_cells_test.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"\n✓ 可视化报告已生成：{output_path}")
print("请在浏览器中打开查看")
