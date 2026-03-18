#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终分割逻辑
"""

import re

def final_split_logic():
    """最终的分割逻辑"""
    
    # 原始文本
    order_text = "蕊芯1Pe白底漆10桶，规格28,24-4-8 哑光银珠:1桶规格20PE稀释剂:1桶规格180"
    
    # 移除客户名称
    text = order_text.replace("蕊芯1", "").strip()
    
    print(f"=== 最终分割逻辑测试 ===")
    print(f"原始: {order_text}")
    print(f"处理: {text}")
    
    # 手动精确分割
    products = []
    
    # 第一步：按逗号分割
    comma_pos = text.find('，')
    if comma_pos > 0:
        # 第一部分：Pe白底漆10桶
        first_part = text[:comma_pos].strip()
        
        # 第二部分：规格28,24-4-8 哑光银珠:1桶规格20PE稀释剂:1桶规格180
        second_part = text[comma_pos+1:].strip()
        
        print(f"\n第一步分割:")
        print(f"第一部分: {first_part}")
        print(f"第二部分: {second_part}")
        
        # 1. 处理第一个产品：Pe白底漆10桶 + 规格28
        # 提取规格信息
        spec_match = re.search(r'规格(\d+)', second_part)
        if spec_match:
            spec = spec_match.group(1)
            first_product = f"{first_part}规格{spec}"
            products.append(first_product)
            print(f"第一个产品: {first_product}")
        
        # 2. 处理第二个产品：24-4-8 哑光银珠:1桶规格20
        # 跳过规格信息，找到真正的产品
        remaining = second_part
        # 移除已处理的规格部分
        if spec_match:
            remaining = remaining.replace(spec_match.group(0), "", 1)
        
        print(f"剩余部分: {remaining}")
        
        # 查找冒号分隔的产品
        colon_matches = re.findall(r'([^:]*?):(\d+桶(?:规格\d+)?)', remaining)
        print(f"冒号匹配: {colon_matches}")
        
        for match in colon_matches:
            product_name = match[0].strip()
            quantity_info = match[1].strip()
            
            # 跳过空产品名和规格信息
            if not product_name or product_name.startswith('规格') or product_name == '':
                continue
            
            # 特殊处理产品名称
            if '哑光银珠' in product_name or '-' in product_name:
                # 这是第二个产品：24-4-8 哑光银珠:1桶规格20
                product = f"{product_name}:{quantity_info}"
                products.append(product)
                print(f"第二个产品: {product}")
            elif 'PE稀释剂' in product_name:
                # 这是第三个产品：PE稀释剂:1桶规格180
                product = f"{product_name}:{quantity_info}"
                products.append(product)
                print(f"第三个产品: {product}")
    
    print(f"\n=== 最终结果 ===")
    for i, product in enumerate(products, 1):
        print(f"产品 {i}: {product}")
    
    return products

if __name__ == "__main__":
    final_split_logic()