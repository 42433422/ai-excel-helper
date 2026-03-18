#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试完整的前端到后端流程
"""

import requests
import json

def test_api_endpoint():
    """测试API端点"""
    api_url = "http://localhost:5000/api/generate"
    
    # 测试用例
    test_cases = [
        {
            "order_text": "七彩乐园一桶9803规格28",
            "custom_mode": False,
            "number_mode": True
        },
        {
            "order_text": "七彩乐园一桶9803规格28",
            "custom_mode": False,
            "number_mode": False
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}:")
        print(f"订单文本: {test_case['order_text']}")
        print(f"编号模式: {test_case['number_mode']}")
        print("=" * 80)
        
        # 构建请求数据
        data = {
            "order_text": test_case["order_text"],
            "template_name": "尹玉华1.xlsx",
            "custom_mode": test_case["custom_mode"],
            "number_mode": test_case["number_mode"]
        }
        
        try:
            # 发送请求
            response = requests.post(api_url, json=data, timeout=30)
            
            print(f"响应状态码: {response.status_code}")
            
            # 解析响应
            result = response.json()
            print(f"成功: {result.get('success', False)}")
            print(f"消息: {result.get('message', '无')}")
            
            if result.get('success'):
                # 打印解析结果
                parsed_data = result.get('parsed_data', {})
                print(f"\n解析结果:")
                print(f"购买单位: {parsed_data.get('purchase_unit', '未知')}")
                print(f"产品名称: {parsed_data.get('product_name', '未知')}")
                print(f"产品型号: {parsed_data.get('model_number', '未知')}")
                
                # 打印产品列表
                products = parsed_data.get('products', [])
                if products:
                    print(f"\n产品列表:")
                    for j, product in enumerate(products, 1):
                        print(f"\n产品 {j}:")
                        print(f"  型号: {product.get('model_number', '未知')}")
                        print(f"  名称: {product.get('name', '未知')}")
                        print(f"  数量: {product.get('quantity_kg', 0)}")
                        print(f"  单价: {product.get('unit_price', 0)}")
                        print(f"  金额: {product.get('amount', 0)}")
            else:
                print(f"错误详情: {result.get('message', '无')}")
                
        except Exception as e:
            print(f"测试失败: {e}")
        
        print("=" * 80)

def test_shipment_parser():
    """测试ShipmentParser"""
    import sys
    import os
    
    # 添加AI助手目录到Python路径
    sys.path.append(os.path.join(os.path.dirname(__file__), 'AI助手'))
    
    from shipment_parser import ShipmentParser
    
    parser = ShipmentParser()
    
    # 测试文本
    test_text = "七彩乐园一桶9803规格28"
    
    print(f"\n测试ShipmentParser:")
    print(f"测试文本: {test_text}")
    print("=" * 80)
    
    # 测试编号模式
    result = parser.parse(test_text, number_mode=True)
    print(f"编号模式解析结果:")
    print(f"购买单位: {result.get('purchase_unit', '未知')}")
    print(f"产品名称: {result.get('product_name', '未知')}")
    print(f"产品型号: {result.get('model_number', '未知')}")
    print(f"数量: {result.get('quantity_kg', 0)}")
    
    # 测试名称模式
    result_name_mode = parser.parse(test_text, number_mode=False)
    print(f"\n名称模式解析结果:")
    print(f"购买单位: {result_name_mode.get('purchase_unit', '未知')}")
    print(f"产品名称: {result_name_mode.get('product_name', '未知')}")
    print(f"产品型号: {result_name_mode.get('model_number', '未知')}")
    print(f"数量: {result_name_mode.get('quantity_kg', 0)}")
    
    print("=" * 80)

if __name__ == "__main__":
    test_api_endpoint()
    test_shipment_parser()
