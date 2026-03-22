# -*- coding: utf-8 -*-
"""
快速验证脚本 - 检查所有组件是否正常
"""

import sys
import os

print("=" * 80)
print("标签模板生成器 - 快速验证")
print("=" * 80)
print()

# 1. 检查后端模块
print("1. 检查后端模块...")
try:
    from app.services.skills.label_template_generator import get_label_template_generator_skill
    print("   ✓ label_template_generator 模块加载成功")
    
    skill = get_label_template_generator_skill()
    print(f"   ✓ 技能加载成功：{skill.name}")
except Exception as e:
    print(f"   ✗ 模块加载失败：{e}")
    sys.exit(1)

# 2. 检查条形码生成器
print("\n2. 检查条形码生成器...")
try:
    from app.services.skills.label_template_generator.barcode_generator import BarcodeGenerator
    
    bc = BarcodeGenerator('code128')
    print(f"   ✓ BarcodeGenerator 加载成功")
    print(f"   ✓ 支持类型：{bc.get_supported_types()}")
except Exception as e:
    print(f"   ✗ 条形码生成器加载失败：{e}")

# 3. 检查依赖库
print("\n3. 检查依赖库...")
try:
    from PIL import Image
    print("   ✓ Pillow 已安装")
except ImportError:
    print("   ✗ Pillow 未安装")

try:
    import barcode
    print("   ✓ python-barcode 已安装")
except ImportError:
    print("   ✗ python-barcode 未安装")

try:
    import pytesseract
    print("   ✓ pytesseract 已安装 (OCR)")
except ImportError:
    print("   ⚠ pytesseract 未安装 (OCR 功能将不可用)")

# 4. 检查前端构建
print("\n4. 检查前端构建...")
vue_dist = os.path.join(os.path.dirname(__file__), 'templates', 'vue-dist')
if os.path.exists(vue_dist):
    print(f"   ✓ 前端构建目录存在：{vue_dist}")
    
    # 检查 TemplatePreviewView 是否构建
    import glob
    files = glob.glob(os.path.join(vue_dist, 'assets', 'js', '*TemplatePreviewView*.js'))
    if files:
        print(f"   ✓ TemplatePreviewView 已构建：{os.path.basename(files[0])}")
    else:
        print("   ✗ TemplatePreviewView 未找到")
else:
    print(f"   ✗ 前端构建目录不存在：{vue_dist}")

# 5. 检查 API 路由
print("\n5. 检查 API 路由...")
try:
    from app.routes.skills import skills_bp
    print("   ✓ skills 蓝图已注册")
except Exception as e:
    print(f"   ✗ skills 蓝图加载失败：{e}")

try:
    from app.routes.excel_templates import excel_templates_bp
    print("   ✓ excel_templates 蓝图已注册")
except Exception as e:
    print(f"   ✗ excel_templates 蓝图加载失败：{e}")

# 6. 测试条形码生成
print("\n6. 测试条形码生成...")
try:
    img = bc.generate("163500001")
    if img:
        print(f"   ✓ 条形码生成成功 (尺寸：{img.size})")
    else:
        print("   ✗ 条形码生成失败")
except Exception as e:
    print(f"   ✗ 条形码生成异常：{e}")

print("\n" + "=" * 80)
print("验证完成！")
print("=" * 80)
print()
print("访问地址：http://localhost:5000/console?view=excel")
print()
print("如果所有检查项都通过，说明系统已就绪！")
print()
