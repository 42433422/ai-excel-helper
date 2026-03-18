#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试打印机分配逻辑
"""

import requests
import json

def test_printer_assignment():
    """测试打印机分配"""
    
    try:
        # 调用打印机API
        response = requests.get('http://127.0.0.1:5000/api/printers')
        
        if response.status_code == 200:
            data = response.json()
            
            print("=== 打印机分配测试结果 ===")
            print(f"总打印机数: {data.get('count', 0)}")
            
            if data.get('success'):
                # 检查分类结果
                classified = data.get('classified', {})
                
                document_printer = classified.get('document_printer', {})
                label_printer = classified.get('label_printer', {})
                
                print(f"\n📄 发货单打印机:")
                print(f"  名称: {document_printer.get('name', '未分配')}")
                print(f"  状态: {document_printer.get('status', '未知')}")
                print(f"  连接: {'✅' if document_printer.get('is_connected') else '❌'}")
                
                print(f"\n🏷️ 标签打印机:")
                print(f"  名称: {label_printer.get('name', '未分配')}")
                print(f"  状态: {label_printer.get('status', '未知')}")
                print(f"  连接: {'✅' if label_printer.get('is_connected') else '❌'}")
                
                # 检查是否都正确分配
                summary = data.get('summary', {})
                print(f"\n📊 总结:")
                print(f"  发货单打印机就绪: {'✅' if summary.get('document_printer_ready') else '❌'}")
                print(f"  标签打印机就绪: {'✅' if summary.get('label_printer_ready') else '❌'}")
                print(f"  全部就绪: {'✅' if summary.get('all_ready') else '❌'}")
                
                # 检查详细列表
                printers = data.get('printers', [])
                print(f"\n📋 详细打印机列表:")
                for i, printer in enumerate(printers):
                    name = printer.get('name', 'Unknown')
                    printer_type = printer.get('type', '未分类')
                    is_default = printer.get('is_default', False)
                    print(f"  {i+1}. {name} - {printer_type} {'(默认)' if is_default else ''}")
                
                return True
            else:
                print(f"❌ API返回错误: {data.get('message', '未知错误')}")
                return False
        else:
            print(f"❌ API请求失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    print("开始测试打印机分配...")
    success = test_printer_assignment()
    print(f"\n测试结果: {'✅ 通过' if success else '❌ 失败'}")
