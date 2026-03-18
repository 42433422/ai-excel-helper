#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试蕊芯订单解析
"""

import urllib.request
import json

def test_ruixin_order():
    # 测试订单文本
    order_text = "蕊芯1Pe白底漆10桶，规格28KG,24-4-8 哑光银珠:1桶，规格20Kg，PE稀释剂:1桶，规格180KG"
    
    print(f"=== 测试订单解析 ===")
    print(f"订单文本: {order_text}")
    
    try:
        # 测试解析API
        test_data = {
            'order_text': order_text
        }
        
        json_data = json.dumps(test_data).encode('utf-8')
        
        request = urllib.request.Request(
            'http://localhost:5000/api/shipment/parse',
            data=json_data,
            headers={'Content-Type': 'application/json'}
        )
        
        response = urllib.request.urlopen(request, timeout=10)
        result = json.loads(response.read().decode())
        
        print(f'\n✅ API响应状态: {response.status}')
        
        if result.get('success'):
            print(f"✅ 解析成功!")
            data = result.get('data', {})
            
            print(f"\n📋 解析结果:")
            print(f"  客户单位: {data.get('purchase_unit', '未识别')}")
            print(f"  产品数量: {len(data.get('products', []))}个")
            
            for i, product in enumerate(data.get('products', []), 1):
                print(f"\n  产品 {i}:")
                print(f"    名称: {product.get('name', '未知')}")
                print(f"    型号: {product.get('model_number', '未知')}")
                print(f"    数量: {product.get('quantity_tins', 0)}桶")
                print(f"    规格: {product.get('tin_spec', 0)}kg/桶")
                print(f"    总重量: {product.get('quantity_kg', 0)}kg")
                print(f"    单价: ¥{product.get('unit_price', 0)}")
                print(f"    金额: ¥{product.get('amount', 0)}")
        else:
            print(f"❌ 解析失败: {result.get('message', '未知错误')}")
            
    except Exception as e:
        print(f'❌ API测试失败: {e}')

if __name__ == "__main__":
    test_ruixin_order()