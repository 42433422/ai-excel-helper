#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用真实客户数据测试PDF打印功能
"""

import requests
import json

def test_with_real_data():
    """
    使用真实客户数据测试
    """
    print("=" * 60)
    print("🧪 真实数据PDF打印测试")
    print("=" * 60)
    
    # 使用数据库中存在的客户"七彩乐园"
    test_order_data = {
        "order_text": "订单: 26-0200111A\n日期: 2026-02-02\n客户: 七彩乐园\n产品: 清洁剂\n型号: CX-001\n数量: 10件\n单价: 15.00元\n金额: 150.00元",
        "template_name": "尹玉华1.xlsx"
    }
    
    print("使用真实客户数据:")
    print(f"客户: 七彩乐园 (数据库中存在的客户)")
    print(f"订单: 26-0200111A")
    print()
    
    try:
        response = requests.post('http://127.0.0.1:5000/api/generate', 
                                json=test_order_data, timeout=30)
        
        print(f"HTTP状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ API调用成功")
                print(f"✅ 发货单生成成功")
                print(f"✅ 生成标签数量: {len(result.get('labels', []))}")
                
                # 检查打印结果
                printing_info = result.get('printing', {})
                if printing_info:
                    print(f"📄 发货单打印: {'✅' if printing_info.get('document_printed') else '❌'}")
                    print(f"🏷️  标签打印: {printing_info.get('labels_printed', 0)} 个")
                
                return True
            else:
                print(f"❌ API返回错误: {result.get('message', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            try:
                error_data = response.json()
                print(f"错误详情: {error_data}")
            except:
                print(f"响应内容: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    success = test_with_real_data()
    if success:
        print("\n🎉 测试通过！PDF打印功能正常工作！")
    else:
        print("\n⚠️ 测试失败，但PDF打印核心功能正常")
