#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打印机配置诊断工具
用于诊断和解决默认打印机冲突问题
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_printer_configuration():
    """测试打印机配置"""
    try:
        print("=" * 70)
        print("🔍 打印机配置诊断工具")
        print("=" * 70)
        
        # 导入必要的模块
        from win32print import EnumPrinters, PRINTER_ENUM_LOCAL
        from app_api import get_document_printer, get_label_printer, validate_printer_separation, get_printers
        
        print("\n📋 1. 获取系统打印机列表")
        printers = EnumPrinters(PRINTER_ENUM_LOCAL, None, 1)
        print(f"   检测到 {len(printers)} 台打印机:")
        
        for i, printer in enumerate(printers, 1):
            printer_name = printer[2]
            print(f"   {i}. {printer_name}")
            
            # 分析打印机类型
            printer_name_lower = printer_name.lower()
            printer_type = "未知"
            if any(keyword in printer_name_lower for keyword in ['tsc', 'ttp', 'label', '标签', 'thermal', 'barcode']):
                printer_type = "条码/标签打印机"
            elif any(keyword in printer_name_lower for keyword in ['joli', '24-pin', 'dot matrix', 'impact', 'lq', '针式']):
                printer_type = "点阵/发货单打印机"
            else:
                printer_type = "通用打印机"
            
            print(f"      -> 类型: {printer_type}")
        
        print("\n📊 2. 测试打印机识别函数")
        
        # 测试发货单打印机
        print("\n   🖨️ 测试发货单打印机识别:")
        doc_printer = get_document_printer()
        if doc_printer:
            print(f"   ✅ 识别结果: {doc_printer}")
        else:
            print("   ❌ 未找到发货单打印机")
        
        # 测试标签打印机
        print("\n   🏷️ 测试标签打印机识别:")
        label_printer = get_label_printer()
        if label_printer:
            print(f"   ✅ 识别结果: {label_printer}")
        else:
            print("   ❌ 未找到标签打印机")
        
        print("\n🔍 3. 打印机分离性验证")
        validation = validate_printer_separation()
        
        if validation['valid']:
            print("   ✅ 打印机配置验证通过")
            print(f"   📄 发货单打印机: {validation['doc_printer']}")
            print(f"   🏷️ 标签打印机: {validation['label_printer']}")
        else:
            print("   ❌ 打印机配置验证失败")
            print(f"   🔴 错误: {validation['error']}")
        
        print("\n💡 4. 解决建议")
        
        if len(printers) == 0:
            print("   🔴 问题: 未检测到任何打印机")
            print("   💡 解决方案: 请确保打印机已正确连接并安装驱动程序")
        elif len(printers) == 1:
            print("   ⚠️ 问题: 系统中只有1台打印机")
            print("   💡 解决方案: ")
            print("      1. 安装独立的标签打印机")
            print("      2. 或设置手动打印模式")
            print("      3. 在Windows中设置默认打印机")
        elif validation['valid']:
            print("   ✅ 打印机配置正确")
            print("   💡 建议: 保持当前配置，测试打印功能")
        else:
            print("   🔴 问题: 打印机配置冲突")
            print("   💡 解决方案: ")
            if doc_printer == label_printer:
                print("      1. 重新命名打印机，确保两个名称不同")
                print("      2. 重新安装打印机驱动程序")
                print("      3. 检查Windows打印机设置")
            else:
                print("      1. 检查打印机驱动程序")
                print("      2. 重新连接打印机")
                print("      3. 重启系统")
        
        print("\n🔧 5. 故障排除步骤")
        print("   步骤1: 检查物理连接")
        print("   步骤2: 验证驱动程序")
        print("   步骤3: 测试Windows打印功能")
        print("   步骤4: 重启系统")
        print("   步骤5: 联系技术支持")
        
        print("\n" + "=" * 70)
        print("✅ 诊断完成")
        print("=" * 70)
        
        return validation['valid']
        
    except Exception as e:
        print(f"❌ 诊断过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_individual_printers():
    """测试单个打印机"""
    try:
        print("\n🧪 6. 单个打印机测试")
        
        from app_api import get_document_printer, get_label_printer
        
        # 测试发货单打印机
        print("\n   📄 发货单打印机测试:")
        doc_printer = get_document_printer()
        if doc_printer:
            print(f"   ✅ 发货单打印机: {doc_printer}")
            
            # 测试发送打印作业
            try:
                import win32print
                hPrinter = win32print.OpenPrinter(doc_printer)
                # 获取默认打印作业
                info = win32print.GetPrinter(hPrinter, 2)
                print(f"   📊 状态: {'就绪' if info.get('Status') == 0 else '错误'}")
                win32print.ClosePrinter(hPrinter)
            except Exception as e:
                print(f"   ⚠️ 无法获取状态: {e}")
        else:
            print("   ❌ 未找到发货单打印机")
        
        # 测试标签打印机
        print("\n   🏷️ 标签打印机测试:")
        label_printer = get_label_printer()
        if label_printer:
            print(f"   ✅ 标签打印机: {label_printer}")
            
            # 测试发送打印作业
            try:
                import win32print
                hPrinter = win32print.OpenPrinter(label_printer)
                info = win32print.GetPrinter(hPrinter, 2)
                print(f"   📊 状态: {'就绪' if info.get('Status') == 0 else '错误'}")
                win32print.ClosePrinter(hPrinter)
            except Exception as e:
                print(f"   ⚠️ 无法获取状态: {e}")
        else:
            print("   ❌ 未找到标签打印机")
        
    except Exception as e:
        print(f"❌ 单个打印机测试失败: {e}")

if __name__ == "__main__":
    print("🚀 启动打印机诊断工具...")
    print("请确保AI助手系统已关闭或正在运行")
    
    success = test_printer_configuration()
    test_individual_printers()
    
    print("\n🎯 总结:")
    if success:
        print("✅ 打印机配置正确，可以进行打印测试")
    else:
        print("❌ 打印机配置存在问题，请根据上述建议进行修复")
