import sys
sys.path.insert(0, r'E:\FHD\XCAGI')

from app.services.skills.label_template_generator.label_template_generator import extract_text_with_ocr
import json
import glob

# 使用 glob 匹配文件
png_files = glob.glob(r"E:\FHD\*PE*.png")
if not png_files:
    print("未找到测试图片")
    sys.exit(1)

img_path = png_files[0]
print(f"测试图片：{img_path}\n")

print("开始分析图片...\n")
result = extract_text_with_ocr(img_path, use_regions=False)

if result['success']:
    print("识别成功\n")
    
    # 打印网格信息
    grid = result.get('grid', {})
    print(f"=== 网格结构 ===")
    print(f"行数：{grid.get('rows', 0)}")
    print(f"列数：{grid.get('cols', 0)}")
    
    # 打印单元格详情
    cells = grid.get('cells', [])
    print(f"\n=== 单元格详情 (共{len(cells)}个) ===")
    for cell in cells:
        print(f"单元格 [{cell['row']},{cell['col']}]: 位置=({cell['x']}, {cell['y']}), 尺寸={cell['width']}x{cell['height']}")
    
    # 打印字段
    print(f"\n=== 识别的字段 (共{len(result['fields'])}个) ===")
    for i, field in enumerate(result['fields'], 1):
        print(f"{i}. {field['label']}: {field['value']} (类型：{field['type']}, 置信度：{field['confidence']:.2f})")
    
    # 输出简化版 JSON（只显示关键字段）
    print("\n=== 网格配置 (JSON) ===")
    grid_config = {
        'image_size': {'width': 900, 'height': 600},
        'grid_size': {
            'rows': grid.get('rows', 0),
            'cols': grid.get('cols', 0)
        },
        'cells': cells,
        'fields': result['fields']
    }
    print(json.dumps(grid_config, indent=2, ensure_ascii=False))
else:
    print(f"✗ 识别失败：{result.get('error', '未知错误')}")
