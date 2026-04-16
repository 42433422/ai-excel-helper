# -*- coding: utf-8 -*-
"""
完整的标签图片网格检测器 - 支持合并单元格
"""

import cv2
import numpy as np
import json

# 读取图片
import glob
files = glob.glob(r'e:\FHD\26-0300001A*.png')
image_path = files[0]

print(f"读取图片：{image_path}")

with open(image_path, 'rb') as f:
    file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
img_array = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

height, width = img_array.shape[:2]
print(f"图片尺寸：{width} x {height}，比例 {width/height:.2f}:1")
print("=" * 70)

# 转换为灰度图
gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)

# 二值化 - 只检测非常黑的像素（表格边框）
_, binary = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)

# 显示二值化统计
black_pixels = np.sum(binary > 0)
print(f"黑色像素：{black_pixels} ({black_pixels / binary.size * 100:.2f}%)")

# ============ 检测水平线 ============
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
    # 水平线：连续黑色像素超过图片宽度 50%
    if max_continuous > gray.shape[1] * 0.5:
        horizontal_lines.append(y)

# ============ 检测垂直线 ============
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
    # 垂直线：连续黑色像素超过图片高度 50%
    if max_continuous > gray.shape[0] * 0.5:
        vertical_lines.append(x)

print(f"\n原始线条：")
print(f"  水平线：{len(horizontal_lines)} 条")
print(f"  垂直线：{len(vertical_lines)} 条")

# ============ 合并线条 ============
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

print(f"\n合并后线条：")
print(f"  水平线：{len(horizontal_lines)} 条 {horizontal_lines}")
print(f"  垂直线：{len(vertical_lines)} 条 {vertical_lines}")

# ============ 分析单元格和合并情况 ============
print(f"\n" + "=" * 70)
print("单元格分析")
print("=" * 70)

def analyze_cells(horizontal_lines, vertical_lines):
    """分析单元格，包括合并单元格"""
    rows = len(horizontal_lines) - 1
    cols = len(vertical_lines) - 1

    cells = []
    for i in range(rows):
        for j in range(cols):
            x = vertical_lines[j]
            y = horizontal_lines[i]
            w = vertical_lines[j + 1] - x
            h = horizontal_lines[i + 1] - y

            cell = {
                'row': i,
                'col': j,
                'x': x,
                'y': y,
                'width': w,
                'height': h,
                'is_merged_horizontally': False,
                'is_merged_vertically': False,
                'merge_width': 1,
                'merge_height': 1
            }
            cells.append(cell)

    # 检测水平合并（跨多列）
    for cell in cells:
        # 检查是否水平延伸（检查右侧是否有边框缺失）
        if cell['col'] < cols - 1:
            # 计算该单元格右侧边框的连续黑色像素
            right_border_x = cell['x'] + cell['width']
            border_continuous = 0
            max_continuous = 0
            for y in range(cell['y'], cell['y'] + cell['height']):
                if y < gray.shape[0] and right_border_x < gray.shape[1]:
                    if binary[y, right_border_x] > 0:
                        border_continuous += 1
                    else:
                        if border_continuous > max_continuous:
                            max_continuous = border_continuous
                        border_continuous = 0
            if border_continuous > max_continuous:
                max_continuous = border_continuous

            # 如果右侧边框大部分不是黑色，可能是合并单元格
            if max_continuous < cell['height'] * 0.5:
                cell['is_merged_horizontally'] = True

    # 检测垂直合并（跨多行）
    for cell in cells:
        if cell['row'] < rows - 1:
            bottom_border_y = cell['y'] + cell['height']
            border_continuous = 0
            max_continuous = 0
            for x in range(cell['x'], cell['x'] + cell['width']):
                if x < gray.shape[1] and bottom_border_y < gray.shape[0]:
                    if binary[bottom_border_y, x] > 0:
                        border_continuous += 1
                    else:
                        if border_continuous > max_continuous:
                            max_continuous = border_continuous
                        border_continuous = 0
            if border_continuous > max_continuous:
                max_continuous = border_continuous

            if max_continuous < cell['width'] * 0.5:
                cell['is_merged_vertically'] = True

    return cells

cells = analyze_cells(horizontal_lines, vertical_lines)

print(f"\n基本网格：{len(horizontal_lines)-1} 行 x {len(vertical_lines)-1} 列")
print(f"检测到 {len(cells)} 个单元格")

print("\n单元格详情：")
for i, cell in enumerate(cells):
    status = []
    if cell['is_merged_horizontally']:
        status.append("水平合并")
    if cell['is_merged_vertically']:
        status.append("垂直合并")
    status_str = ", ".join(status) if status else "正常"

    print(f"  [{i:2d}] 行{cell['row']} 列{cell['col']}: "
          f"位置({cell['x']:3d},{cell['y']:3d}) "
          f"尺寸{cell['width']:3d}x{cell['height']:3d} "
          f"[{status_str}]")

# ============ 生成 HTML 报告 ============
html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>标签网格分析报告 - {width}x{height}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        h1 {{
            text-align: center;
            color: #333;
            margin-bottom: 20px;
        }}
        .info {{
            text-align: center;
            color: #666;
            margin-bottom: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 4px;
        }}
        .preview-container {{
            display: flex;
            gap: 30px;
            margin-bottom: 20px;
        }}
        .canvas-wrapper {{
            background: #fafafa;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 20px;
        }}
        canvas {{
            border: 2px solid #333;
        }}
        .analysis-panel {{
            flex: 1;
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 4px;
            padding: 20px;
            max-height: 600px;
            overflow-y: auto;
        }}
        .section {{
            margin-bottom: 20px;
        }}
        .section h3 {{
            color: #007bff;
            margin-bottom: 10px;
            border-bottom: 2px solid #007bff;
            padding-bottom: 5px;
        }}
        .cell-grid {{
            display: grid;
            gap: 5px;
        }}
        .cell {{
            padding: 8px;
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 12px;
        }}
        .cell.merged-h {{
            background: #fff3cd;
            border-color: #ffc107;
        }}
        .cell.merged-v {{
            background: #d4edda;
            border-color: #28a745;
        }}
        .cell.merged-both {{
            background: #f8d7da;
            border-color: #dc3545;
        }}
        .cell-num {{
            font-weight: bold;
            color: #333;
        }}
        .cell-pos {{
            color: #666;
            font-size: 10px;
        }}
        .cell-size {{
            color: #007bff;
            font-size: 10px;
        }}
        .grid-lines {{
            background: white;
            padding: 15px;
            border-radius: 4px;
            margin-top: 10px;
        }}
        .lines-row {{
            display: flex;
            gap: 20px;
            margin: 10px 0;
        }}
        .lines-col {{
            flex: 1;
        }}
        .lines-col h4 {{
            margin-bottom: 8px;
            color: #333;
        }}
        .lines-list {{
            list-style: none;
            font-family: monospace;
            font-size: 12px;
        }}
        .lines-list li {{
            padding: 3px 8px;
            margin: 2px 0;
            background: #f8f9fa;
            border-radius: 3px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📋 标签图片网格分析报告</h1>

        <div class="info">
            <strong>图片尺寸：{width} × {height}</strong> |
            比例 {width/height:.2f}:1 |
            黑色像素 {black_pixels} ({black_pixels / binary.size * 100:.2f}%)
        </div>

        <div class="preview-container">
            <div class="canvas-wrapper">
                <canvas id="gridCanvas" width="{width}" height="{height}"></canvas>
            </div>

            <div class="analysis-panel">
                <div class="section">
                    <h3>📊 基本信息</h3>
                    <div class="grid-lines">
                        <div><strong>水平线：</strong>{len(horizontal_lines)} 条</div>
                        <div><strong>垂直线：</strong>{len(vertical_lines)} 条</div>
                        <div><strong>网格结构：</strong>{len(horizontal_lines)-1} 行 × {len(vertical_lines)-1} 列</div>
                        <div><strong>单元格数：</strong>{len(cells)} 个</div>
                    </div>
                </div>

                <div class="section">
                    <h3>📏 线条坐标</h3>
                    <div class="lines-row">
                        <div class="lines-col">
                            <h4>水平线 Y</h4>
                            <ul class="lines-list">
'''
for i, y in enumerate(horizontal_lines):
    html_content += f'                                <li>[{i}] Y = {y}</li>\n'

html_content += '''                            </ul>
                        </div>
                        <div class="lines-col">
                            <h4>垂直线 X</h4>
                            <ul class="lines-list">
'''
for i, x in enumerate(vertical_lines):
    html_content += f'                                <li>[{i}] X = {x}</li>\n'

html_content += '''                            </ul>
                        </div>
                    </div>
                </div>

                <div class="section">
                    <h3>🔲 单元格详情</h3>
                    <div class="cell-grid" style="grid-template-columns: repeat(3, 1fr);">
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
    status_str = ", ".join(status_text) if status_text else "正常"

    html_content += f'''                        <div class="cell {status_class}">
                            <div class="cell-num">#{cell['row']},{cell['col']}</div>
                            <div class="cell-pos">({cell['x']},{cell['y']})</div>
                            <div class="cell-size">{cell['width']}x{cell['height']}</div>
                            <div>{status_str}</div>
                        </div>
'''

html_content += '''                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const canvas = document.getElementById('gridCanvas');
        const ctx = canvas.getContext('2d');

        const horizontalLines = ''' + json.dumps(horizontal_lines) + ''';
        const verticalLines = ''' + json.dumps(vertical_lines) + ''';
        const cells = ''' + json.dumps(cells) + ''';

        function drawCanvas() {
            // 清空画布
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // 白色背景
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            // 绘制单元格
            cells.forEach((cell, index) => {
                let fillColor = 'rgba(0, 123, 255, 0.1)';
                let borderColor = '#007bff';

                if (cell.is_merged_horizontally && cell.is_merged_vertically) {
                    fillColor = 'rgba(220, 53, 69, 0.2)';
                    borderColor = '#dc3545';
                } else if (cell.is_merged_horizontally) {
                    fillColor = 'rgba(255, 193, 7, 0.2)';
                    borderColor = '#ffc107';
                } else if (cell.is_merged_vertically) {
                    fillColor = 'rgba(40, 167, 69, 0.2)';
                    borderColor = '#28a745';
                }

                // 填充颜色
                ctx.fillStyle = fillColor;
                ctx.fillRect(cell.x, cell.y, cell.width, cell.height);

                // 边框
                ctx.strokeStyle = borderColor;
                ctx.lineWidth = 2;
                ctx.strokeRect(cell.x, cell.y, cell.width, cell.height);

                // 单元格编号
                ctx.fillStyle = '#333';
                ctx.font = 'bold 12px Microsoft YaHei';
                ctx.fillText(`${index}`, cell.x + 5, cell.y + 15);
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

            // 绘制边框（加粗）
            ctx.strokeStyle = '#000';
            ctx.lineWidth = 3;
            ctx.strokeRect(0, 0, canvas.width, canvas.height);
        }

        drawCanvas();

        // 添加鼠标悬停提示
        canvas.addEventListener('mousemove', (e) => {
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            const mouseX = (e.clientX - rect.left) * scaleX;
            const mouseY = (e.clientY - rect.top) * scaleY;

            let found = false;
            cells.forEach((cell, index) => {
                if (mouseX >= cell.x && mouseX <= cell.x + cell.width &&
                    mouseY >= cell.y && mouseY <= cell.y + cell.height) {
                    canvas.title = `#${index} 位置(${cell.x},${cell.y}) 尺寸${cell.width}x${cell.height}`;
                    found = true;
                }
            });

            if (!found) {
                canvas.title = '';
            }
        });
    </script>
</body>
</html>
'''

output_path = r'e:\FHD\grid_analyzer_report.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"\n" + "=" * 70)
print(f"✓ 分析报告已生成：{output_path}")
print(f"请在浏览器中打开查看完整的网格分析结果")
print("=" * 70)

# 输出 JSON 数据供后端使用
print("\nJSON 数据：")
data = {
    'width': width,
    'height': height,
    'horizontal_lines': horizontal_lines,
    'vertical_lines': vertical_lines,
    'cells': cells,
    'grid': {
        'rows': len(horizontal_lines) - 1,
        'cols': len(vertical_lines) - 1,
        'total_cells': len(cells)
    }
}
print(json.dumps(data, indent=2, ensure_ascii=False))
