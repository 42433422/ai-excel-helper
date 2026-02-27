#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复AI型号识别问题
"""

import sys
import os
import json
import requests

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def fix_ai_model_recognition():
    """修复AI型号识别问题"""
    
    # 蕊芯家私1的产品型号映射
    ruixin_products = {
        "PE白底漆": {
            "model": "9806",
            "spec": "28.0KG",
            "price": "10.1"
        },
        "PE稀释剂": {
            "model": "9806A", 
            "spec": "180.0KG",
            "price": "7.0"
        },
        "PU哑光浅灰银珠漆": {
            "model": "24-4-8*",
            "spec": "20.0KG", 
            "price": "24.0"
        }
    }
    
    # 优化的提示词
    prompt = f"""你是一个专业的订单解析助手，专注于从订单文本中提取准确的产品信息。

重要规则：

1. 客户识别规则：
   - "蕊芯1" 应该识别为 "蕊芯家私1"
   - "蕊芯" (单独) 应该识别为 "蕊芯家私"
   - 避免将数字"1"识别为客户或产品编号

2. 产品型号识别规则（蕊芯家私专属）：
   蕊芯家私1的产品型号如下：
   - PE白底漆 → 型号必须是 "9806"
   - PE稀释剂 → 型号必须是 "9806A"
   - 哑光银珠漆 → 型号必须是 "24-4-8*"

3. 产品识别规则：
   - 产品编号通常是字母+数字组合（如9806、8520F等）
   - 产品名称通常是描述性文本（如PE白底漆、哑光银珠漆、稀释剂等）
   - 不要将"规格"、"桶"、"KG"等描述性文字识别为产品
   - 不要将"PE"识别为产品型号，PE是产品类型

4. 数量识别：
   - "10桶"表示10桶
   - "规格28KG"表示每桶28公斤规格
   - 总重量 = 桶数 × 桶规格

请以JSON格式返回结果：
{{
    "purchase_unit": "购买单位",
    "products": [
        {{
            "name": "产品名称",
            "model_number": "产品型号（必须按照上述规则）",
            "quantity_tins": 桶数,
            "quantity_kg": 总重量,
            "tin_spec": 桶规格
        }}
    ]
}}

现在请解析以下订单："""
    
    # 测试订单
    test_orders = [
        "蕊芯Pe白底漆10桶，规格28KGPE稀释剂:1桶，规格180KG",
        "蕊芯1Pe白底漆10桶，规格28KGPE稀释剂:1桶，规格180KG"
    ]
    
    print("=" * 70)
    print("🤖 测试修复后的AI型号识别")
    print("=" * 70)
    
    for i, order_text in enumerate(test_orders, 1):
        print(f"\n🧪 测试订单 {i}:")
        print(f"订单: {order_text}")
        
        # 调用AI
        api_key = os.environ.get("DEEPSEEK_API_KEY", "your-api-key-here")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": order_text}
            ],
            "temperature": 0.1,  # 降低温度，提高准确性
            "max_tokens": 2000,
            "response_format": {"type": "json_object"}
        }
        
        try:
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                parsed_result = json.loads(content)
                
                print(f"\n✅ AI解析结果:")
                print(f"  客户单位: {parsed_result.get('purchase_unit', '未识别')}")
                print(f"  产品数量: {len(parsed_result.get('products', []))}个")
                
                # 检查客户匹配
                purchase_unit = parsed_result.get('purchase_unit', '')
                if i == 1 and "蕊芯家私" in purchase_unit:
                    print(f"  ✅ 客户匹配成功: {purchase_unit}")
                elif i == 2 and "蕊芯家私1" in purchase_unit:
                    print(f"  ✅ 客户匹配成功: {purchase_unit}")
                else:
                    print(f"  ⚠️  客户匹配结果: {purchase_unit}")
                
                # 显示产品信息
                products = parsed_result.get('products', [])
                print(f"\n📦 产品详情:")
                for j, product in enumerate(products, 1):
                    print(f"  产品 {j}:")
                    print(f"    名称: {product.get('name', '未知')}")
                    print(f"    型号: {product.get('model_number', '无')}")
                    print(f"    数量: {product.get('quantity_tins', 0)}桶")
                    print(f"    规格: {product.get('tin_spec', 0)}kg/桶")
                    print(f"    总重量: {product.get('quantity_kg', 0)}kg")
                    
                    # 验证型号
                    name = product.get('name', '')
                    model = product.get('model_number', '')
                    if 'PE白底漆' in name and model == '9806':
                        print(f"    ✅ 型号正确")
                    elif 'PE稀释剂' in name and model == '9806A':
                        print(f"    ✅ 型号正确")
                    elif '哑光银珠' in name and model == '24-4-8*':
                        print(f"    ✅ 型号正确")
                    else:
                        print(f"    ⚠️  型号需要验证: {model}")
                        
            else:
                print(f"  ❌ API调用失败: {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ AI提取失败: {e}")
        
        print("-" * 60)

if __name__ == "__main__":
    fix_ai_model_recognition()