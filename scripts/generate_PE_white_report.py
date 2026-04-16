# -*- coding: utf-8 -*-
"""
PE白底漆 标签网格分析报告
"""

import cv2
import numpy as np
import json
import glob

# 读取图片
files = glob.glob(r'e:\FHD\26-0300001A_第1项_PE白底漆.png')
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

# 构建单元格
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
            'should_merge_down': False
        }

        # 检测右侧边框
        if j < cols - 1:
            right_border_x = x + w
            border_black_count = 0
            for check_y in range(y, y + h):
                if check_y < gray.shape[0] and right_border_x < gray.shape[1]:
                    if binary[check_y, right_border_x] > 0:
                        border_black_count += 1
            if h > 0 and border_black_count < h * 0.5:
                cell['should_merge_right'] = True

        # 检测底部边框
        if i < rows - 1:
            bottom_border_y = y + h
            border_black_count = 0
            for check_x in range(x, x + w):
                if check_x < gray.shape[1] and bottom_border_y < gray.shape[0]:
                    if binary[bottom_border_y, check_x] > 0:
                        border_black_count += 1
            if w > 0 and border_black_count < w * 0.5:
                cell['should_merge_down'] = True

        cells.append(cell)

# 生成 HTML
html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>PE白底漆 标签网格分析</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }}
        h1 {{ text-align: center; color: #333; }}
        .info {{ text-align: center; color: #666; margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 4px; }}
        .preview {{ display: flex; gap: 30px; }}
        .canvas-wrapper {{ background: #fafafa; padding: 20px; border-radius: 4px; }}
        canvas {{ border: 3px solid #333; }}
        .details {{ flex: 1; background: #f8f9fa; padding: 20px; border-radius: 4px; max-height: 600px; overflow-y: auto; }}
        .section {{ margin-bottom: 20px; }}
        .section h3 {{ color: #007bff; border-bottom: 2px solid #007bff; padding-bottom: 5px; }}
        .cell-grid {{ display: grid; gap: 5px; }}
        .cell {{ padding: 10px; background: white; border-radius: 4px; border-left: 4px solid #007bff; }}
        .cell.merged-h {{ background: #fff3cd; border-left-color: #ffc107; }}
        .cell.merged-v {{ background: #d4edda; border-left-color: #28a745; }}
        .cell.merged-both {{ background: #f8d7da; border-left-color: #dc3545; }}
        .legend {{ display: flex; gap: 20px; justify-content: center; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📋 PE白底漆 标签网格分析报告</h1>

        <div class="info">
            <strong>图片尺寸：{width} × {height}</strong> |
            <strong>网格结构：{rows} 行 × {cols} 列</strong> |
            <strong>单元格数：{len(cells)}</strong>
        </div>

        <div class="preview">
            <div class="canvas-wrapper">
                <canvas id="canvas" width="{width}" height="{height}"></canvas>
            </div>

            <div class="details">
                <div class="section">
                    <h3>网格线坐标</h3>
                    <div><strong>水平线 Y：</strong>{horizontal_lines}</div>
                    <div><strong>垂直线 X：</strong>{vertical_lines}</div>
                </div>

                <div class="section">
                    <h3>单元格详情</h3>
                    <div class="cell-grid" style="grid-template-columns: repeat({cols}, 1fr);">
'''

for cell in cells:
    css_class = ""
    if cell['should_merge_right'] and cell['should_merge_down']:
        css_class = "merged-both"
    elif cell['should_merge_right']:
        css_class = "merged-h"
    elif cell['should_merge_down']:
        css_class = "merged-v"

    status = []
    if cell['should_merge_right']:
        status.append("水平合并")
    if cell['should_merge_down']:
        status.append("垂直合并")
    status_str = ", ".join(status) if status else "独立"

    html_content += f'''                        <div class="cell {css_class}">
                            <div><strong>#[{cell['row']},{cell['col']}]</strong> {status_str}</div>
                            <div>位置: ({cell['x']}, {cell['y']})</div>
                            <div>尺寸: {cell['width']}×{cell['height']}</div>
                        </div>
'''

html_content += '''                    </div>
                </div>
            </div>
        </div>

        <div class="legend">
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 20px; height: 20px; background: rgba(0,123,255,0.2); border: 2px solid #007bff; border-radius: 4px;"></div>
                <span>独立单元格</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 20px; height: 20px; background: rgba(255,193,7,0.3); border: 2px solid #ffc107; border-radius: 4px;"></div>
                <span>水平合并</span>
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

                if (cell.should_merge_right && cell.should_merge_down) {
                    fillColor = 'rgba(220, 53, 69, 0.2)';
                    borderColor = '#dc3545';
                } else if (cell.should_merge_right) {
                    fillColor = 'rgba(255, 193, 7, 0.3)';
                    borderColor = '#ffc107';
                } else if (cell.should_merge_down) {
                    fillColor = 'rgba(40, 167, 69, 0.3)';
                    borderColor = '#28a745';
                }

                ctx.fillStyle = fillColor;
                ctx.fillRect(cell.x, cell.y, cell.width, cell.height);

                ctx.strokeStyle = borderColor;
                ctx.lineWidth = 2;
                ctx.strokeRect(cell.x, cell.y, cell.width, cell.height);

                ctx.fillStyle = '#333';
                ctx.font = 'bold 14px Microsoft YaHei';
                ctx.fillText(`[${cell.row},${cell.col}]`, cell.x + 5, cell.y + 20);
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

output_path = r'e:\FHD\PE白底漆_grid_report.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"✓ 报告已生成：{output_path}")
print(f"\n检测结果：")
print(f"  网格结构：{rows} 行 × {cols} 列")
print(f"  水平合并：{sum(1 for c in cells if c['should_merge_right'])} 个")
print(f"  垂直合并：{sum(1 for c in cells if c['should_merge_down'])} 个")
