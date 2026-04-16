# -*- coding: utf-8 -*-
"""
复制标签图片到无中文路径
"""
import os
import shutil

# 源文件路径（使用 glob 找到的）
src_files = [
    r'e:\FHD\26-0300001A_第 1 项_PE 封固底漆稀料.png',
    r'e:\FHD\XCAGI\resources\ai_assistant\商标导出\26-0300001A_第 1 项_PE 封固底漆稀料.png'
]

# 目标路径
dst_path = r'e:\FHD\test_label.png'

for src in src_files:
    try:
        if os.path.exists(src):
            print(f"找到文件：{src}")
            shutil.copy2(src, dst_path)
            print(f"✓ 已复制到：{dst_path}")
            break
    except Exception as e:
        print(f"❌ 复制失败：{e}")
else:
    print("❌ 未找到任何源文件")
