#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用标准格式测试打印任务分配
"""

import os
import sys
import json
import time
import requests

def test_with_standard_format():
    """使用标准格式测试"""
    print("=" * 80)
    print("🚀 使用标准格式测试打印任务分配")
    print("=" * 80)
    
    try:
        # 1. 检查Flask应用状态
        print("\n📋 1. 检查Flask应用状态")
        try:
            response = requests.get("http://127.0.0.1:5000/api/printers", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Flask应用正常运行")
                print(f"📋 打印机信息:")
                print(json.dumps(data, ensure_ascii=False, indent=2))
            else:
                print(f"❌ Flask应用状态异常: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 无法连接Flask应用: {e}")
            return False
        
        # 2. 准备标准格式的测试数据
        print("\n📋 2. 准备标准格式测试数据")
        
        # 使用更简单的格式
        test_orders = [
            # 格式1：简单产品
            "七彩乐园 铁观音 500g 2罐 120元",
            # 格式2：带订单号
            "订单26-0200201A: 七彩乐园 铁观音 500g 2罐 120元",
        ]
        
        for i, order_text in enumerate(test_orders):
            print(f"\n测试 {i+1}: {order_text}")
            
            test_order = {
                "order_text": order_text,
                "template_name": "尹玉华1.xlsx",
                "custom_mode": False,
                "number_mode": False,
                "excel_sync": False,
                "auto_print": True
            }
            
            print("发送测试请求...")
            
            try:
                response = requests.post(
                    "http://127.0.0.1:5000/api/generate",
                    json=test_order,
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ 响应状态: {result.get('success')}")
                    
                    if result.get('success'):
                        print(f"✅ 订单生成成功")
                        
                        # 检查是否有解析结果
                        if 'parsed_data' in result:
                            parsed = result['parsed_data']
                            print(f"📋 解析结果:")
                            print(f"   购买单位: {parsed.get('purchase_unit', '未知')}")
                            print(f"   产品数: {len(parsed.get('products', []))}")
                            
                            products = parsed.get('products', [])
                            for j, product in enumerate(products):
                                print(f"   产品{j+1}: {product.get('name', '未知')}")
                        
                        # 检查打印结果
                        if 'printing' in result:
                            printing = result['printing']
                            print(f"\n📊 打印结果:")
                            print(f"   发货单打印: {printing.get('document_printed', False)}")
                            print(f"   标签打印: {printing.get('labels_printed', 0)}")
                            print(f"   发货单结果: {printing.get('document_result', '未知')}")
                            print(f"   标签结果: {printing.get('labels_result', '未知')}")
                        else:
                            print(f"⚠️ 响应中没有打印结果")
                    else:
                        print(f"❌ 订单生成失败")
                        print(f"   消息: {result.get('message', '未知')}")
                        
                        # 显示解析结果
                        if 'parsed_data' in result:
                            parsed = result['parsed_data']
                            print(f"   解析结果:")
                            print(f"   产品数: {len(parsed.get('products', []))}")
                            
                            if not parsed.get('products'):
                                print(f"   ⚠️ 没有解析到产品，可能是订单格式问题")
                                print(f"   原始文本: {parsed.get('raw_text', '无')}")
                                
                                print(f"\n💡 建议使用更标准的订单格式:")
                                print(f"   格式: 产品名称 规格 数量 单位 价格")
                                print(f"   示例: 七彩乐园 铁观音 500g 2罐 120元")
                        
                else:
                    print(f"❌ HTTP错误: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ 请求失败: {e}")
        
        # 3. 总结
        print("\n" + "=" * 80)
        print("📊 测试总结")
        print("=" * 80)
        
        print("\n💡 提示:")
        print("   1. 使用标准格式的订单文本")
        print("   2. 格式: 产品名称 规格 数量 单位 价格")
        print("   3. 确保产品名称在模板中存在")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_print_without_auto():
    """测试不自动打印，只生成订单"""
    print("\n" + "=" * 80)
    print("🚀 测试不自动打印的订单生成")
    print("=" * 80)
    
    try:
        test_order = {
            "order_text": "七彩乐园 铁观音 500g 2罐 120元",
            "template_name": "尹玉华1.xlsx",
            "custom_mode": False,
            "number_mode": False,
            "excel_sync": False,
            "auto_print": False  # 不自动打印
        }
        
        print(f"测试订单: {test_order['order_text']}")
        print(f"自动打印: {test_order['auto_print']}")
        
        response = requests.post(
            "http://127.0.0.1:5000/api/generate",
            json=test_order,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"响应状态: {result.get('success')}")
            
            if result.get('success'):
                print(f"✅ 订单生成成功")
                
                # 显示生成的文件
                if 'document' in result:
                    doc = result['document']
                    print(f"📄 生成的发货单:")
                    print(f"   文件名: {doc.get('filename', '未知')}")
                    print(f"   路径: {doc.get('output_path', '未知')}")
                
                # 显示标签
                if 'labels' in result:
                    labels = result['labels']
                    print(f"🏷️ 生成的标签: {len(labels)} 个")
                    for i, label in enumerate(labels):
                        print(f"   标签{i+1}: {label.get('filename', '未知')}")
                
                return result
            else:
                print(f"❌ 订单生成失败")
                print(f"   消息: {result.get('message', '未知')}")
                return None
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None

if __name__ == "__main__":
    print("🚀 开始测试...")
    
    # 先测试不自动打印
    result = test_print_without_auto()
    
    if result:
        print("\n✅ 订单生成成功，可以手动测试打印功能")
        print("💡 下一步:")
        print("   1. 启用自动打印选项")
        print("   2. 重新发送订单")
        print("   3. 检查打印任务是否正确分配")
    else:
        print("\n❌ 订单生成失败，请检查订单格式")
        print("💡 建议:")
        print("   1. 使用标准格式: 产品名称 规格 数量 单位 价格")
        print("   2. 确保产品名称在模板中存在")
        print("   3. 检查模板文件是否正确")
