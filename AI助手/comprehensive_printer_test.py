#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合测试：模拟实际业务场景中的发货单打印问题
"""

import sys
import os
import logging

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger(__name__)

def test_shipment_document_printing():
    """
    测试发货单打印的实际业务场景
    """
    print("=" * 70)
    print("🔍 综合测试：模拟发货单打印机实际业务场景")
    print("=" * 70)
    
    try:
        # 1. 模拟数据库中的订单数据
        from app_api import generate_single_order
        from shipment_document import ShipmentDocumentGenerator
        
        # 2. 测试打印机识别一致性
        from app_api import get_document_printer, get_label_printer
        
        print("\n📋 1. 验证打印机识别一致性")
        doc_printer = get_document_printer()
        label_printer = get_label_printer()
        
        print(f"   发货单打印机: {doc_printer}")
        print(f"   标签打印机: {label_printer}")
        
        if doc_printer == label_printer:
            print("   ❌ 错误：发货单和标签打印机相同！")
            return False
        else:
            print("   ✅ 正确：发货单和标签打印机已分离")
        
        # 3. 检查是否混用了TSC打印机
        if 'TSC' in str(doc_printer) or 'TTP' in str(doc_printer):
            print("   ❌ 严重错误：发货单打印机被设置为TSC条码打印机！")
            print("   📄 当前发货单打印机配置错误")
            return False
        else:
            print("   ✅ 正确：发货单打印机不是TSC条码打印机")
        
        # 4. 测试模拟生成发货单并打印
        print("\n📄 2. 测试发货单生成和打印流程")
        
        # 模拟一个简单的订单数据
        test_order_data = {
            'order_number': 'TEST-2026-001',
            'customer_name': '测试客户',
            'products': [
                {
                    'product_name': '测试产品A',
                    'product_number': 'TEST-001',
                    'quantity': 2,
                    'unit': '个'
                }
            ]
        }
        
        print("   🔄 尝试生成测试发货单...")
        
        # 生成发货单
        generator = ShipmentDocumentGenerator()
        
        # 创建输出目录
        output_dir = "outputs"
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, "test_shipment_document.pdf")
        
        try:
            result = generator.generate_document(test_order_data, output_path)
            print(f"   📄 发货单生成结果: {result}")
            
            if result and os.path.exists(output_path):
                print("   ✅ 发货单文件生成成功")
                
                # 5. 测试实际打印
                print("\n🖨️ 3. 测试发货单实际打印")
                
                from print_utils import print_document
                
                print(f"   📄 打印文件: {output_path}")
                print(f"   🖨️ 目标打印机: {doc_printer}")
                
                # 执行打印
                print_result = print_document(output_path, doc_printer)
                
                print(f"   📊 打印结果: {print_result}")
                
                if print_result.get('success', False):
                    print("   ✅ 发货单打印成功")
                    
                    # 6. 验证打印机的正确性
                    print("\n🔍 4. 验证打印机的正确性")
                    print(f"   📄 发货单应打印到: {doc_printer}")
                    print(f"   🏷️ 标签应打印到: {label_printer}")
                    
                    if 'TSC' in doc_printer:
                        print("   ❌ 错误确认：发货单被发送到TSC打印机！")
                        return False
                    else:
                        print("   ✅ 正确：发货单发送到正确的打印机")
                    
                    return True
                else:
                    print("   ❌ 发货单打印失败")
                    print(f"   错误详情: {print_result}")
                    return False
            else:
                print("   ❌ 发货单文件生成失败")
                return False
                
        except Exception as e:
            print(f"   ❌ 生成发货单时出错: {e}")
            return False
        
    except Exception as e:
        print(f"   ❌ 测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_printer_configuration_edge_cases():
    """
    测试打印机配置的边界情况
    """
    print("\n" + "=" * 70)
    print("⚠️ 边界情况测试：打印机配置问题排查")
    print("=" * 70)
    
    try:
        from app_api import get_document_printer, get_label_printer
        
        # 多次调用测试稳定性
        print("\n🔄 1. 测试打印机识别稳定性（连续调用10次）")
        
        doc_printers = []
        label_printers = []
        
        for i in range(10):
            doc_printer = get_document_printer()
            label_printer = get_label_printer()
            
            doc_printers.append(doc_printer)
            label_printers.append(label_printer)
            
            print(f"   第{i+1}次: 发货单={doc_printer}, 标签={label_printer}")
        
        # 检查一致性
        doc_consistent = len(set(doc_printers)) == 1
        label_consistent = len(set(label_printers)) == 1
        
        print(f"\n   📊 识别稳定性分析:")
        print(f"   发货单打印机一致性: {'✅' if doc_consistent else '❌'}")
        print(f"   标签打印机一致性: {'✅' if label_consistent else '❌'}")
        
        # 检查最终配置
        final_doc = doc_printers[-1]
        final_label = label_printers[-1]
        
        print(f"\n   📋 最终打印机配置:")
        print(f"   发货单打印机: {final_doc}")
        print(f"   标签打印机: {final_label}")
        
        # 检查TSC混淆问题
        tsc_in_doc = 'TSC' in final_doc or 'TTP' in final_doc
        same_printer = final_doc == final_label
        
        print(f"\n   🔍 潜在问题检查:")
        print(f"   TSC在发货单打印机中: {'❌ 是' if tsc_in_doc else '✅ 否'}")
        print(f"   发货单和标签打印机相同: {'❌ 是' if same_printer else '✅ 否'}")
        
        if tsc_in_doc:
            print("   ❌ 严重问题：发货单打印机包含TSC，确认为错误配置！")
            return False
        elif same_printer:
            print("   ⚠️ 警告：发货单和标签使用同一打印机")
            return False
        else:
            print("   ✅ 打印机配置正常")
            return True
        
    except Exception as e:
        print(f"   ❌ 边界测试异常: {e}")
        return False

if __name__ == "__main__":
    print("🧪 开始综合发货单打印机测试")
    
    # 测试1：实际业务场景
    test1_result = test_shipment_document_printing()
    
    # 测试2：边界情况
    test2_result = test_printer_configuration_edge_cases()
    
    print("\n" + "=" * 70)
    print("📊 测试总结")
    print("=" * 70)
    
    if test1_result and test2_result:
        print("✅ 所有测试通过！发货单打印机配置正常")
    elif test2_result:
        print("⚠️ 边界测试通过，但实际打印测试有问题")
    else:
        print("❌ 发现问题！发货单打印机配置需要修复")
    
    print(f"\n测试结果:")
    print(f"   实际业务场景: {'✅' if test1_result else '❌'}")
    print(f"   边界情况: {'✅' if test2_result else '❌'}")