# -*- coding: utf-8 -*-
"""
验证合并后的单元格并生成可视化报告
"""

import cv2
import numpy as np
import json
import glob

# 读取图片
files = glob.glob(r'e:\FHD\26-0300001A*.png')
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

# 第一步：构建基础单元格并检测边框缺失
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
            'should_merge_right': False
        }

        # 检测右侧边框
        if j < cols - 1:
            right_border_x = x + w
            border_black_count = 0
            for check_y in range(y, y + h):
                if check_y < gray.shape[0] and right_border_x < gray.shape[1]:
                    if binary[check_y, right_border_x] > 0:
                        border_black_count += 1

            if border_black_count < h * 0.5:
                cell['should_merge_right'] = True

        cells.append(cell)

# 第二步：实际合并单元格
merged_cells = []
visited = set()

for i in range(rows):
    for j in range(cols):
        cell_id = f"{i},{j}"
        if cell_id in visited:
            continue

        cell = next((c for c in cells if c['row'] == i and c['col'] == j), None)
        if not cell:
            continue

        merge_count = 1
        while cell['should_merge_right'] and j + merge_count < cols:
            visited.add(f"{i},{j + merge_count}")
            merge_count += 1
            if j + merge_count < cols:
                next_cell = next((c for c in cells if c['row'] == i and c['col'] == j + merge_count), None)
                if next_cell:
                    cell = next_cell
                else:
                    break

        merged_cells.append({
            'row': i,
            'start_col': j,
            'end_col': j + merge_count - 1,
            'merge_cols': merge_count,
            'x': vertical_lines[j],
            'y': horizontal_lines[i],
            'width': vertical_lines[j + merge_count] - vertical_lines[j],
            'height': horizontal_lines[i + 1] - horizontal_lines[i],
            'original_cols': list(range(j, j + merge_count)),
            'is_merged': merge_count > 1
        })

        visited.add(cell_id)

# 生成 HTML 报告
html_content = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>合并单元格最终结果</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }}
        h1 {{ text-align: center; color: #333; margin-bottom: 10px; }}
        .info {{ text-align: center; color: #666; margin-bottom: 30px; }}
        .preview {{ display: flex; gap: 30px; }}
        .canvas-wrapper {{ background: #fafafa; padding: 30px; border-radius: 4px; }}
        canvas {{ border: 3px solid #333; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }}
        .result-panel {{ flex: 1; background: #f8f9fa; padding: 20px; border-radius: 4px; max-height: 600px; overflow-y: auto; }}
        .section {{ margin-bottom: 20px; }}
        .section h3 {{ color: #007bff; margin-bottom: 10px; border-bottom: 2px solid #007bff; padding-bottom: 5px; }}
        .cell {{ padding: 12px; margin: 8px 0; background: white; border-radius: 4px; border-left: 4px solid #007bff; }}
        .cell.merged {{ background: #fff3cd; border-left-color: #ffc107; }}
        .cell-header {{ font-weight: bold; font-size: 16px; margin-bottom: 5px; }}
        .cell-detail {{ color: #666; font-size: 13px; }}
        .summary {{ background: #e7f3ff; padding: 15px; border-radius: 4px; margin-bottom: 20px; }}
        .summary-item {{ display: inline-block; margin-right: 30px; }}
        .summary-value {{ font-weight: bold; color: #007bff; font-size: 24px; }}
        .legend {{ display: flex; gap: 30px; justify-content: center; margin-top: 20px; }}
        .legend-item {{ display: flex; align-items: center; gap: 8px; }}
        .legend-color {{ width: 24px; height: 24px; border-radius: 4px; border: 2px solid; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📋 合并单元格检测结果</h1>
        <div class="info">图片尺寸：{width} × {height} | 基本网格：{rows} 行 × {cols} 列</div>

        <div class="summary">
            <div class="summary-item">
                <div>原始单元格</div>
                <div class="summary-value">{rows * cols}</div>
            </div>
            <div class="summary-item">
                <div>合并后单元格</div>
                <div class="summary-value">{len(merged_cells)}</div>
            </div>
            <div class="summary-item">
                <div>合并的组数</div>
                <div class="summary-value">{sum(1 for c in merged_cells if c['is_merged'])}</div>
            </div>
        </div>

        <div class="preview">
            <div class="canvas-wrapper">
                <canvas id="canvas" width="{width}" height="{height}"></canvas>
            </div>

            <div class="result-panel">
                <div class="section">
                    <h3>📊 合并单元格详情</h3>
'''

for mc in merged_cells:
    css_class = "cell merged" if mc['is_merged'] else "cell"
    merge_info = f"合并了 {mc['merge_cols']} 列 (原始列: {mc['original_cols']})" if mc['is_merged'] else "独立单元格"

    html_content += f'''                    <div class="{css_class}">
                        <div class="cell-header">#[{mc['row']},{mc['start_col']}] {merge_info}</div>
                        <div class="cell-detail">
                            位置: ({mc['x']}, {mc['y']}) |
                            尺寸: {mc['width']} × {mc['height']}
                        </div>
                    </div>
'''

html_content += '''                </div>
            </div>
        </div>

        <div class="legend">
            <div class="legend-item">
                <div class="legend-color" style="background: rgba(0,123,255,0.2); border-color: #007bff;"></div>
                <span>独立单元格</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: rgba(255,193,7,0.3); border-color: #ffc107;"></div>
                <span>水平合并单元格</span>
            </div>
        </div>
    </div>

    <script>
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');

        const mergedCells = ''' + json.dumps(merged_cells, ensure_ascii=False) + ''';
        const horizontalLines = ''' + json.dumps(horizontal_lines) + ''';
        const verticalLines = ''' + json.dumps(vertical_lines) + ''';

        function draw() {
            // 清空
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            // 绘制合并后的单元格
            mergedCells.forEach((cell, index) => {
                let fillColor = cell.is_merged
                    ? 'rgba(255, 193, 7, 0.3)'
                    : 'rgba(0, 123, 255, 0.2)';
                let borderColor = cell.is_merged ? '#ffc107' : '#007bff';

                ctx.fillStyle = fillColor;
                ctx.fillRect(cell.x, cell.y, cell.width, cell.height);

                ctx.strokeStyle = borderColor;
                ctx.lineWidth = cell.is_merged ? 3 : 2;
                ctx.strokeRect(cell.x, cell.y, cell.width, cell.height);

                // 单元格编号
                ctx.fillStyle = '#333';
                ctx.font = 'bold 16px Microsoft YaHei';
                ctx.fillText(
                    `[${cell.row},${cell.start_col}]`,
                    cell.x + 5,
                    cell.y + 25
                );

                // 显示是否合并
                if (cell.is_merged) {
                    ctx.font = '12px Microsoft YaHei';
                    ctx.fillText(
                        `合并${cell.merge_cols}列`,
                        cell.x + 5,
                        cell.y + 45
                    );
                }
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

output_path = r'e:\FHD\final_merged_result.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"✓ 最终合并结果报告已生成：{output_path}")
print(f"\n合并统计：")
print(f"  原始单元格：{rows * cols} 个")
print(f"  合并后单元格：{len(merged_cells)} 个")
print(f"  合并的组数：{sum(1 for c in merged_cells if c['is_merged'])} 组")
