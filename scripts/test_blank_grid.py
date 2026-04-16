# -*- coding: utf-8 -*-
"""
测试空白网格模板 - 验证网格检测逻辑
"""

from PIL import Image, ImageDraw

# 创建空白图片（模拟标签尺寸）
width = 600
height = 600
image = Image.new('RGB', (width, height), 'white')
draw = ImageDraw.Draw(image)

# 绘制外边框
draw.rectangle([0, 0, width-1, height-1], outline='black', width=2)

# 绘制水平分隔线（模拟表格行）
horizontal_lines = [
    120,   # 第 1 行底部
    240,   # 第 2 行底部
    360,   # 第 3 行底部
    480,   # 第 4 行底部
]

for y in horizontal_lines:
    draw.line([(0, y), (width, y)], fill='black', width=1)

# 绘制垂直分隔线（模拟表格列）
vertical_lines = [
    200,   # 第 1 列右侧
    400,   # 第 2 列右侧
]

for x in vertical_lines:
    draw.line([(x, 0), (x, height)], fill='black', width=1)

# 保存图片
output_path = r'e:\FHD\blank_grid_template.png'
image.save(output_path)

print(f"✓ 空白网格模板已生成：{output_path}")
print(f"  图片尺寸：{width} x {height}")
print(f"  水平线：5 条（包括上下边框）")
print(f"  垂直线：4 条（包括左右边框）")
print(f"  单元格：4 行 x 3 列 = 12 个")
