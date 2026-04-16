# -*- coding: utf-8 -*-
"""
生成实际标签图片的 HTML 预览 - 使用实际检测数据
"""

import cv2
import numpy as np
import os
import json

# 使用 glob 找到实际文件
import glob
files = glob.glob(r'e:\FHD\26-0300001A*.png')
image_path = files[0]

print(f"读取图片：{image_path}")

# 读取图片
with open(image_path, 'rb') as f:
    file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
img_array = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

height, width = img_array.shape[:2]
print(f"图片尺寸：{width} x {height}")

# 转换为灰度图
gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)

# 二值化
_, binary = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)

# 检测水平线
horizontal_lines = []
for y in range(gray.shape[0]):
    row = binary[y, :]
    max_continuous_length = 0
    current_length = 0
    for x in range(len(row)):
        if row[x] > 0:
            current_length += 1
        else:
            if current_length > max_continuous_length:
                max_continuous_length = current_length
            current_length = 0
    if current_length > max_continuous_length:
        max_continuous_length = current_length
    if max_continuous_length > gray.shape[1] * 0.5:
        horizontal_lines.append(y)

# 检测垂直线
vertical_lines = []
for x in range(gray.shape[1]):
    col = binary[:, x]
    max_continuous_length = 0
    current_length = 0
    for y in range(len(col)):
        if col[y] > 0:
            current_length += 1
        else:
            if current_length > max_continuous_length:
                max_continuous_length = current_length
            current_length = 0
    if current_length > max_continuous_length:
        max_continuous_length = current_length
    if max_continuous_length > gray.shape[0] * 0.5:
        vertical_lines.append(x)

# 合并线条
def merge_very_close_lines(lines, threshold=5):
    if not lines:
        return []
    merged = [lines[0]]
    for line in lines[1:]:
        if line - merged[-1] > threshold:
            merged.append(line)
        else:
            merged[-1] = (merged[-1] + line) // 2
    return merged

def merge_close_lines(lines, threshold=50):
    if not lines:
        return []
    merged = [lines[0]]
    for line in lines[1:]:
        if line - merged[-1] > threshold:
            merged.append(line)
    return merged

horizontal_lines = sorted(list(set(horizontal_lines)))
vertical_lines = sorted(list(set(vertical_lines)))

horizontal_lines = merge_very_close_lines(horizontal_lines, threshold=5)
vertical_lines = merge_very_close_lines(vertical_lines, threshold=5)

horizontal_lines = merge_close_lines(horizontal_lines, threshold=50)
vertical_lines = merge_close_lines(vertical_lines, threshold=50)

print(f"\n网格线检测结果:")
print(f"  水平线：{horizontal_lines}")
print(f"  垂直线：{vertical_lines}")

# 生成 HTML
html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>实际标签图片预览 - {width}x{height}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 1000px;
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
            font-size: 24px;
        }}
        .info {{
            text-align: center;
            color: #666;
            margin-bottom: 20px;
        }}
        .preview-container {{
            display: flex;
            justify-content: center;
            align-items: flex-start;
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
            border: 1px solid #333;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }}
        .grid-info {{
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 4px;
            padding: 20px;
            min-width: 250px;
        }}
        .grid-info h3 {{
            color: #007bff;
            margin-bottom: 15px;
            border-bottom: 2px solid #007bff;
            padding-bottom: 8px;
        }}
        .info-item {{
            margin: 10px 0;
            padding: 8px;
            background: white;
            border-radius: 4px;
        }}
        .info-label {{
            font-size: 12px;
            color: #666;
        }}
        .info-value {{
            font-size: 16px;
            font-weight: bold;
            color: #333;
            font-family: monospace;
        }}
        .lines-list {{
            list-style: none;
            max-height: 200px;
            overflow-y: auto;
        }}
        .lines-list li {{
            padding: 5px 10px;
            margin: 3px 0;
            background: #f8f9fa;
            border-radius: 3px;
            font-family: monospace;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📋 实际标签图片预览</h1>
        <div class="info">
            <strong>图片尺寸：{width} × {height}</strong> | 比例 {width/height:.2f}:1
        </div>

        <div class="preview-container">
            <div class="canvas-wrapper">
                <canvas id="labelCanvas" width="{width}" height="{height}"></canvas>
            </div>

            <div class="grid-info">
                <h3>📊 网格信息</h3>
                <div class="info-item">
                    <div class="info-label">水平线</div>
                    <div class="info-value">{len(horizontal_lines)} 条</div>
                </div>
                <div class="info-item">
                    <div class="info-label">垂直线</div>
                    <div class="info-value">{len(vertical_lines)} 条</div>
                </div>
                <div class="info-item">
                    <div class="info-label">网格结构</div>
                    <div class="info-value">{len(horizontal_lines)-1}行 × {len(vertical_lines)-1}列</div>
                </div>

                <h3 style="margin-top: 20px;">📏 水平线 Y 坐标</h3>
                <ul class="lines-list">
'''
for i, y in enumerate(horizontal_lines):
    html_content += f'                    <li>[{i}] Y = {y}</li>\n'

html_content += '''                </ul>

                <h3>📐 垂直线 X 坐标</h3>
                <ul class="lines-list">
'''
for i, x in enumerate(vertical_lines):
    html_content += f'                    <li>[{i}] X = {x}</li>\n'

html_content += f'''                </ul>
            </div>
        </div>
    </div>

    <script>
        const canvas = document.getElementById('labelCanvas');
        const ctx = canvas.getContext('2d');

        // 网格数据（从实际图片检测）
        const horizontalLines = {json.dumps(horizontal_lines)};
        const verticalLines = {json.dumps(vertical_lines)};

        function drawCanvas() {{
            // 清空画布
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // 绘制白色背景
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            // 绘制网格线（黑色边框和分隔线）
            ctx.strokeStyle = '#000000';
            ctx.lineWidth = 1;

            // 水平线
            horizontalLines.forEach(y => {{
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(canvas.width, y);
                ctx.stroke();
            }});

            // 垂直线
            verticalLines.forEach(x => {{
                ctx.beginPath();
                ctx.moveTo(x, 0);
                ctx.lineTo(x, canvas.height);
                ctx.stroke();
            }});

            // 绘制边框（加粗）
            ctx.lineWidth = 3;
            ctx.strokeRect(0, 0, canvas.width, canvas.height);
        }}

        drawCanvas();
    </script>
</body>
</html>
'''

# 保存 HTML
output_path = r'e:\FHD\real_label_viewer.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"\n✓ HTML 预览已生成：{output_path}")
print(f"请在浏览器中打开查看实际网格布局")
