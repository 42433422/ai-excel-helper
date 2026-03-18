#!/usr/bin/env python3

import re

# 测试订单
order_text = '温总编号NC50F，NC哑光清面漆3桶规格25单价14.5'

# 提取单价信息
print('测试单价提取：')
unit_price_match = re.search(r'单价(\d+(?:\.\d+)?)', order_text)
if unit_price_match:
    print(f'匹配到单价：{unit_price_match.group(1)}')
    unit_price = float(unit_price_match.group(1))
    print(f'转换后单价：{unit_price}')
else:
    print('没有匹配到单价')

# 提取产品名称
print('\n测试产品名称提取：')
temp_text = order_text
print(f'原始文本：{temp_text}')

# 移除单价信息
temp_text = re.sub(r'\s*单价\d+(?:\.\d+)?', '', temp_text)
print(f'移除单价后：{temp_text}')

# 移除桶数信息
temp_text = re.sub(r'\d+\s*桶', '', temp_text)
print(f'移除桶数后：{temp_text}')

# 移除规格信息
temp_text = re.sub(r'规格\d+(?:\.\d+)?', '', temp_text)
print(f'移除规格后：{temp_text}')

# 移除数量信息（kg等）
temp_text = re.sub(r'\d+(?:\.\d+)?\s*(?:kg|公斤|千克|KG|K)', '', temp_text, flags=re.IGNORECASE)
print(f'移除数量后：{temp_text}')

# 清理并提取产品名称
product_name = temp_text.strip()
print(f'最终产品名称：{product_name}')

# 提取型号
print('\n测试型号提取：')
model_match = re.search(r'(型号|编号)([A-Z0-9-]+)', order_text, re.IGNORECASE)
if model_match:
    print(f'匹配到型号：{model_match.group(0)}')
    print(f'组1：{model_match.group(1)}')
    print(f'组2：{model_match.group(2)}')
else:
    print('没有匹配到型号')

# 提取规格
print('\n测试规格提取：')
spec_match = re.search(r'规格(\d+(?:\.\d+)?)', order_text)
if spec_match:
    print(f'匹配到规格：{spec_match.group(1)}')
else:
    print('没有匹配到规格')

# 提取数量（桶数）
print('\n测试桶数提取：')
tins_match = re.search(r'(\d+)\s*桶', order_text)
if tins_match:
    print(f'匹配到桶数：{tins_match.group(1)}')
else:
    print('没有匹配到桶数')