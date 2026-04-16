# -*- coding: utf-8 -*-
"""
使用 PaddleOCR 3.2.0 表格识别
"""

from paddleocr import TableRecognitionPipelineV2
import json
import glob

# 读取图片
files = glob.glob(r'e:\FHD\26-0300001A*.png')
image_path = files[0]
print(f"读取图片：{image_path}")

# 初始化表格识别管道
print("初始化 TableRecognitionPipelineV2...")
pipeline = TableRecognitionPipelineV2()

print("执行表格识别...")
result = pipeline(image_path)

print(f"\n返回结果类型：{type(result)}")

if result is None:
    print("❌ 未检测到任何内容")
    exit(1)

print(f"\n" + "=" * 70)
print("表格识别结果")
print("=" * 70)

# 打印结果结构
if isinstance(result, dict):
    print(f"结果 keys：{result.keys()}")

    if 'table_html' in result:
        print(f"\n表格 HTML：")
        print(result['table_html'][:500] if len(result.get('table_html', '')) > 500 else result['table_html'])

    if 'table_structure' in result:
        print(f"\n表格结构：")
        print(json.dumps(result['table_structure'], indent=2, ensure_ascii=False)[:1000])

    if 'dt_polys' in result:
        print(f"\n检测到的文本框数量：{len(result['dt_polys'])}")

# 保存完整结果
output_path = r'e:\FHD\paddleocr_table_result.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2, default=str)

print(f"\n✓ 结果已保存到：{output_path}")
