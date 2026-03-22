# -*- coding: utf-8 -*-
"""
标签模板生成器 - 功能演示脚本
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_barcode_generator():
    """测试条形码生成器"""
    print("=" * 80)
    print("测试 1: 条形码生成器")
    print("=" * 80)
    
    try:
        from app.services.skills.label_template_generator.barcode_generator import BarcodeGenerator
        
        # 创建条形码生成器
        bc = BarcodeGenerator('code128')
        print(f"✓ BarcodeGenerator 创建成功")
        print(f"  支持的条码类型：{bc.get_supported_types()}")
        
        # 生成条形码
        data = "163500001"
        img = bc.generate(data)
        if img:
            print(f"✓ 条形码生成成功 (数据：{data})")
            print(f"  图片尺寸：{img.size}")
            
            # 保存图片
            img.save("test_barcode.png")
            print(f"✓ 已保存：test_barcode.png")
        else:
            print("✗ 条形码生成失败")
        
        print()
    except Exception as e:
        print(f"✗ 测试失败：{e}")
        print()


def test_label_template_generator():
    """测试标签模板生成器"""
    print("=" * 80)
    print("测试 2: 标签模板生成器")
    print("=" * 80)
    
    try:
        from app.services.skills.label_template_generator import get_label_template_generator_skill
        
        skill = get_label_template_generator_skill()
        print(f"✓ Label Template Generator Skill 加载成功")
        print(f"  技能名称：{skill.name}")
        print(f"  技能描述：{skill.description}")
        print()
        
        # 测试生成（使用示例图片）
        test_image = r"e:\FHD\oxxf5tzl74p48secr1eq.png"
        
        if os.path.exists(test_image):
            print(f"测试图片：{test_image}")
            print("正在生成标签模板代码...")
            
            result = skill.execute(
                image_path=test_image,
                class_name="TestShoeLabelGenerator",
                enable_ocr=False,
                output_file="test_shoe_label_generator.py",
                verbose=True
            )
            
            if result['success']:
                print(f"✓ 生成成功！")
                print(f"  代码长度：{len(result['code'])} 字符")
                print(f"  输出文件：{result.get('output_file')}")
                
                # 显示代码前 100 行
                print("\n生成的代码片段（前 100 行）:")
                print("-" * 80)
                code_lines = result['code'].split('\n')
                for i, line in enumerate(code_lines[:100]):
                    print(f"{i+1:3d}: {line}")
                print("-" * 80)
            else:
                print(f"✗ 生成失败：{result.get('error', '未知错误')}")
        else:
            print(f"⚠ 测试图片不存在：{test_image}")
        
        print()
    except Exception as e:
        print(f"✗ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        print()


def test_generated_template():
    """测试生成的模板"""
    print("=" * 80)
    print("测试 3: 使用生成的标签模板")
    print("=" * 80)
    
    try:
        # 尝试导入生成的模板
        if os.path.exists("test_shoe_label_generator.py"):
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "test_shoe_label_generator",
                "test_shoe_label_generator.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            GeneratorClass = getattr(module, "TestShoeLabelGenerator", None)
            
            if GeneratorClass:
                print("✓ 生成的模板类加载成功")
                
                # 创建实例
                generator = GeneratorClass(output_dir="./test_labels")
                print(f"✓ 生成器实例创建成功")
                
                # 测试生成标签
                data = {
                    "product_name": "XX 运动鞋",
                    "color": "白色",
                    "item_number": "1635",
                    "code_segment": "00001",
                    "grade": "合格品",
                    "standard": "QB/T4331-2013",
                    "price": "199",
                    "auto_barcode": True
                }
                
                print("\n测试生成标签...")
                filename = generator.generate_label(data, "TEST-001", 1)
                
                if filename:
                    print(f"✓ 标签生成成功：{filename}")
                else:
                    print("✗ 标签生成失败")
            else:
                print("✗ 未找到生成器类")
        else:
            print("⚠ 生成的模板文件不存在，请先运行测试 2")
        
        print()
    except Exception as e:
        print(f"✗ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        print()


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("标签模板生成器 - 功能演示")
    print("=" * 80)
    print()
    
    # 测试 1: 条形码生成器
    test_barcode_generator()
    
    # 测试 2: 标签模板生成器
    test_label_template_generator()
    
    # 测试 3: 生成的模板
    test_generated_template()
    
    print("=" * 80)
    print("所有测试完成！")
    print("=" * 80)
    print()
    print("使用说明:")
    print("1. 访问 http://localhost:5000/console?view=excel")
    print("2. 点击 '📷 从图片生成' 按钮")
    print("3. 上传标签图片")
    print("4. 点击 '🚀 生成模板'")
    print("5. 查看生成的代码和字段")
    print("6. 点击 '✓ 保存为模板'，填写信息并保存")
    print()


if __name__ == "__main__":
    main()
