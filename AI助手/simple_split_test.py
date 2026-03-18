#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化产品分割测试
"""

import re

def simple_split_test():
    """简化的产品分割测试"""
    
    order_text = "蕊芯1Pe白底漆10桶，规格28,24-4-8 哑光银珠:1桶规格20PE稀释剂:1桶规格180"
    
    # 移除客户名称
    text = order_text.replace("蕊芯1", "").strip()
    
    print(f"=== 简化分割测试 ===")
    print(f"原始文本: {order_text}")
    print(f"移除客户后: {text}")
    
    # 手动分析分割
    # 1. 第一个产品：Pe白底漆10桶，规格28
    # 2. 第二个产品：24-4-8 哑光银珠:1桶规格20
    # 3. 第三个产品：PE稀释剂:1桶规格180
    
    # 使用正则表达式分割
    # 模式：产品名 + 数量 + 规格
    pattern = r'(.*?)(?=\d+桶|\d+:|PE|$)'
    
    # 更精确的分割
    # 找到所有的产品开始点
    products = []
    
    # 第一个产品：从开始到第一个逗号
    comma_pos = text.find('，')
    if comma_pos > 0:
        products.append(text[:comma_pos])
        remaining = text[comma_pos+1:]
    else:
        remaining = text
    
    print(f"第一个产品: {products[0] if products else '未找到'}")
    print(f"剩余文本: {remaining}")
    
    # 分析剩余文本
    # 查找产品模式：产品名:数量桶规格数字
    
    # 查找冒号位置
    colon_positions = [i for i, c in enumerate(remaining) if c == ':']
    print(f"冒号位置: {colon_positions}")
    
    # 手动分割
    if len(colon_positions) >= 2:
        # 第一个产品：24-4-8 哑光银珠:1桶规格20
        first_colon = colon_positions[0]
        first_product = remaining[:first_colon] + ":" + remaining[first_colon+1:]
        
        # 查找规格
        spec_match = re.search(r'(\d+)桶规格(\d+)', first_product)
        if spec_match:
            quantity = spec_match.group(1)
            spec = spec_match.group(2)
            first_product = first_product.replace(
                f"{quantity}桶规格{spec}", 
                f"{quantity}桶规格{spec}"
            )
        
        products.append(first_product)
        
        # 第二个产品：PE稀释剂:1桶规格180
        second_colon = colon_positions[1]
        remaining_second = remaining[second_colon+1:]
        spec_match2 = re.search(r'(\d+)桶规格(\d+)', remaining_second)
        if spec_match2:
            quantity2 = spec_match2.group(1)
            spec2 = spec_match2.group(2)
            second_product = "PE稀释剂:" + remaining_second
            products.append(second_product)
    
    print(f"\n分割结果:")
    for i, product in enumerate(products, 1):
        print(f"产品 {i}: {product}")

if __name__ == "__main__":
    simple_split_test()