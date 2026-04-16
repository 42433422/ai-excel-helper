# -*- coding: utf-8 -*-
"""
创建真正有垂直合并的测试图片
"""

from PIL import Image, ImageDraw

# 创建测试图片 - 模拟一个有垂直合并的表格
width = 600
height = 400
image = Image.new('RGB', (width, height), 'white')
draw = ImageDraw.Draw(image)

# 绘制完整边框
draw.rectangle([0, 0, width-1, height-1], outline='black', width=2)

# 水平线
h_lines = [50, 120, 190, 260, 320]
for y in h_lines:
    draw.line([(0, y), (width, y)], fill='black', width=1)

# 垂直线
v_lines = [150, 400, 599]
for x in v_lines:
    draw.line([(x, 0), (x, height)], fill='black', width=1)

# 模拟垂直合并：在第2列，让某些水平分隔线缺失
# 例如：不画第2列在 y=120 处的水平线，使得第1行的第2列和第2行的第2列合并

# 找到第2列的范围
col2_x_start = v_lines[1]  # 150
col2_x_end = v_lines[2]    # 400

# 在 y=120 处，删除第2列的水平线段
# 即从 x=150 到 x=400 之间不画 y=120 这条线
# 但是因为我们用的是 ImageDraw，我们可以通过不画这条线来模拟

# 实际上，更好的方法是画一个跨越多行的矩形边框
# 让我们画一个大的垂直合并单元格

# 画第2列第1行的垂直合并单元格（跨越第1行和第2行）
# 这个单元格从 y=50 到 y=190 (跨越了 h_lines[2]=190 这条线)
merged_top = 50
merged_bottom = 190
merged_left = 150
merged_right = 400

# 擦除第2列在 y=120 处的水平线（在 x=150 到 x=400 之间）
draw.line([(150, 120), (400, 120)], fill='white', width=1)

# 保存测试图片
test_image_path = r'e:\FHD\test_vertical_merge2.png'
image.save(test_image_path)

print(f"✓ 测试图片已创建：{test_image_path}")
print(f"  尺寸：{width} x {height}")
print(f"\n这个测试图片有以下垂直合并：")
print(f"  - 第2列，合并了第1行和第2行")
print(f"  - 合并范围：X=[150,400], Y=[50,190]")
print(f"  - 在 y=120 处，从 x=150 到 x=400 的水平线被擦除了")
