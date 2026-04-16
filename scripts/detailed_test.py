# -*- coding: utf-8 -*-
"""
详细测试 OCR 提取结果 - 捕获所有异常
"""

import traceback
import importlib.util

try:
    spec = importlib.util.spec_from_file_location(
        "label_template_generator",
        r"E:\FHD\XCAGI\app\services\skills\label_template_generator\label_template_generator.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    extract_text_with_ocr = module.extract_text_with_ocr

    # 测试 PE封固底漆稀料
    image_path = r'e:\FHD\26-0300001A_第1项_PE封固底漆稀料.png'

    filename = image_path.split('\\')[-1]
    print(f"测试：{filename}")
    print("=" * 70)

    result = extract_text_with_ocr(image_path)

    if result.get('success'):
        print(f"✓ 成功")
        print(f"\n网格信息：")
        grid = result.get('grid', {})
        print(f"  行 x 列：{grid.get('rows', 0)} 行 × {grid.get('cols', 0)} 列")
        print(f"  水平线 Y：{grid.get('horizontal_lines', [])}")
        print(f"  垂直线 X：{grid.get('vertical_lines', [])}")

        print(f"\n单元格：")
        cells = grid.get('cells', [])
        for i, cell in enumerate(cells):
            print(f"  [{i}] 行{cell.get('row')} 列{cell.get('start_col')}-{cell.get('end_col')} "
                  f"位置({cell.get('x')},{cell.get('y')}) 尺寸{cell.get('width')}x{cell.get('height')}")

        print(f"\n字段：")
        fields = result.get('fields', [])
        for i, field in enumerate(fields):
            print(f"  [{i}] {field.get('label')} = {field.get('value')} (is_merged={field.get('is_merged')})")

    else:
        print(f"✗ 失败：{result.get('error')}")

except Exception as e:
    print(f"✗ 异常：{e}")
    traceback.print_exc()
