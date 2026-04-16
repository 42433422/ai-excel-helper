# -*- coding: utf-8 -*-
"""
调试 _pair_fields_by_grid 函数
"""

import importlib.util
import traceback

spec = importlib.util.spec_from_file_location(
    "label_template_generator",
    r"E:\FHD\XCAGI\app\services\skills\label_template_generator\label_template_generator.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

extract_text_with_ocr = module.extract_text_with_ocr

# 测试
image_path = r'e:\FHD\26-0300001A_第1项_PE封固底漆稀料.png'
filename = image_path.split('\\')[-1]
print(f"测试：{filename}")

result = extract_text_with_ocr(image_path)

if result.get('success'):
    print(f"\n文本块分配到的单元格：")
    text_blocks = result.get('text_blocks', [])
    for i, tb in enumerate(text_blocks):
        print(f"  [{i}] '{tb.get('text')}' -> cell_row={tb.get('cell_row')}, cell_col={tb.get('cell_col')}")

    print(f"\n合并单元格信息：")
    grid = result.get('grid', {})
    cells = grid.get('cells', [])
    for i, cell in enumerate(cells):
        print(f"  [{i}] 行{cell.get('row')} 列{cell.get('start_col')}-{cell.get('end_col')} "
              f"(is_merged={cell.get('end_col') > cell.get('start_col')})")

    print(f"\n字段结果：")
    fields = result.get('fields', [])
    for i, field in enumerate(fields):
        print(f"  [{i}] label='{field.get('label')}' value='{field.get('value')}' is_merged={field.get('is_merged')}")
else:
    print(f"✗ 失败：{result.get('error')}")
