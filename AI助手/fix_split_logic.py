#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复分割逻辑
"""

import re

def test_fixed_split_logic():
    """测试修复后的分割逻辑"""
    
    # 原始文本
    order_text = "蕊芯1Pe白底漆10桶，规格28,24-4-8 哑光银珠:1桶规格20PE稀释剂:1桶规格180"
    
    # 移除客户名称
    text = order_text.replace("蕊芯1", "").strip()
    
    print(f"=== 修复分割逻辑测试 ===")
    print(f"原始: {order_text}")
    print(f"处理: {text}")
    
    # 手动分割
    # 第一步：按逗号分割
    comma_pos = text.find('，')
    first_part = text[:comma_pos]  # "Pe白底漆10桶"
    second_part = text[comma_pos+1:]  # "规格28,24-4-8 哑光银珠:1桶规格20PE稀释剂:1桶规格180"
    
    print(f"\n第一步分割:")
    print(f"第一部分: {first_part}")
    print(f"第二部分: {second_part}")
    
    # 修复：确保第一个产品包含规格信息
    if "规格" in second_part:
        # 提取规格信息
        spec_match = re.search(r'规格(\d+)', second_part)
        if spec_match:
            spec = spec_match.group(1)
            # 将规格信息添加到第一个产品
            first_product = first_part + "规格" + spec
            print(f"第一个产品（包含规格）: {first_product}")
        else:
            first_product = first_part
    else:
        first_product = first_part
    
    products = [first_product]
    
    # 处理第二部分
    # 查找 "24-4-8 哑光银珠:1桶规格20"
    other_match = re.search(r'([^:]*?):(\d+桶(?:规格\d+)?)', second_part)
    if other_match:
        product_name = other_match.group(1).strip()
        quantity_info = other_match.group(2).strip()
        
        # 提取规格
        spec_match = re.search(r'规格(\d+)', quantity_info)
        if spec_match:
            spec = spec_match.group(1)
            # 重新构建产品信息
            before_spec = quantity_info.split('规格')[0]  # "1桶"
            if before_spec:
                product = f"{product_name}:{before_spec}规格{spec}"
                print(f"第二个产品: {product}")
                products.append(product)
    
    # 处理PE稀释剂
    pe_match = re.search(r'PE稀释剂:(\d+桶(?:规格\d+)?)', second_part)
    if pe_match:
        pe_quantity = pe_match.group(1)
        spec_match = re.search(r'规格(\d+)', pe_quantity)
        if spec_match:
            spec = spec_match.group(1)
            pe_quantity_clean = pe_quantity.split('规格')[0]  # "1桶"
            pe_product = f"PE稀释剂:{pe_quantity_clean}规格{spec}"
            print(f"第三个产品: {pe_product}")
            products.append(pe_product)
    
    print(f"\n=== 最终分割结果 ===")
    for i, product in enumerate(products, 1):
        print(f"产品 {i}: {product}")
    
    return products

if __name__ == "__main__":
    test_fixed_split_logic()