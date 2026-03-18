#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试DeepSeek AI的产品提取能力"""

import json
import requests
from config.deepseek_config import DEEPSEEK_API_KEY, DEEPSEEK_API_BASE

class DeepSeekProductExtractor:
    """使用DeepSeek AI提取产品信息"""
    
    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        self.api_base = DEEPSEEK_API_BASE
    
    def extract_products(self, order_text: str) -> dict:
        """从订单文本中提取产品信息"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        system_prompt = """你是一个专业的产品信息提取助手，能够从订单文本中准确提取产品信息。

请从以下订单文本中提取产品信息，格式为JSON，包含：
1. purchase_unit: 购买单位
2. products: 产品列表，每个产品包含：
   - name: 产品名称
   - model_number: 型号（如果有）
   - quantity_tins: 桶数
   - tin_spec: 每桶规格（kg）
   - quantity_kg: 总重量（kg）
   - is_product: 是否为真实产品（true/false）

请严格按照JSON格式输出，不要包含任何额外内容。"""
        
        user_prompt = f"请提取以下订单的产品信息：\n\n{order_text}"
        
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 2000,
            "response_format": {"type": "json_object"}
        }
        
        try:
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                return json.loads(content)
            else:
                print(f"API调用失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"提取失败: {e}")
            return None

# 测试订单
order = '蕊芯家私:Pe白底漆10桶，规格28KG,24-4-8 哑光银珠:1桶，规格20Kg，PE稀释剂:1桶，规格180KG'

print('='*60)
print('测试DeepSeek AI产品提取')
print('='*60)
print()

print(f'原始订单：{order}')
print()

extractor = DeepSeekProductExtractor()
result = extractor.extract_products(order)

if result:
    print('✅ AI提取结果：')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 过滤出真实产品
    real_products = [p for p in result.get('products', []) if p.get('is_product', True)]
    print()
    print(f'识别到 {len(real_products)} 个真实产品：')
    for i, p in enumerate(real_products, 1):
        print(f'{i}. {p["name"]} - {p["quantity_tins"]}桶 x {p["tin_spec"]}kg = {p["quantity_kg"]}kg')
else:
    print('❌ 提取失败')
