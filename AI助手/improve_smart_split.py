#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进智能分割逻辑
"""

import re

def smart_split_products(text: str, purchase_unit: str) -> list:
    """智能分割产品"""
    
    # 移除购买单位
    working_text = text
    if purchase_unit:
        working_text = working_text.replace(purchase_unit, "").strip()
    
    print(f"智能分割测试:")
    print(f"原始文本: {text}")
    print(f"移除客户后: {working_text}")
    
    # 特殊处理这个复杂的格式
    # `Pe白底漆10桶，规格28,24-4-8 哑光银珠:1桶规格20PE稀释剂:1桶规格180`
    
    # 方法1：基于逗号和冒号的分割
    if ',' in working_text and ':' in working_text:
        # 找到第一个逗号
        comma_pos = working_text.find('，')
        if comma_pos > 0:
            # 第一部分：Pe白底漆10桶
            first_part = working_text[:comma_pos]
            
            # 第二部分：规格28,24-4-8 哑光银珠:1桶规格20PE稀释剂:1桶规格180
            second_part = working_text[comma_pos+1:]
            
            products = [first_part]
            
            # 分割第二部分中的产品
            # 查找所有冒号分隔的产品
            colon_products = []
            
            # 使用正则表达式找到所有冒号后的数量信息
            patterns = [
                r'([^:,]+):(\d+桶(?:规格\d+)?)',  # 产品名:数量
                r'(\d+桶规格\d+)([A-Z][^:]*?)(?::|$)',  # 规格产品名
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, second_part)
                if matches:
                    for match in matches:
                        if len(match) == 2:
                            if '桶' in match[1]:
                                # 这是 产品名:数量 格式
                                colon_products.append(f"{match[0]}:{match[1]}")
                            else:
                                # 这是 规格产品名 格式
                                if 'PE' in match[1]:
                                    colon_products.append(f"{match[1]}:{match[0]}")
                        else:
                            # 直接添加匹配到的产品
                            for item in match:
                                if ':' in item or '桶' in item:
                                    colon_products.append(item)
            
            # 如果没有找到冒号产品，尝试基于产品名称分割
            if not colon_products:
                # 查找PE开头的产品
                pe_match = re.search(r'PE稀释剂:.*?规格(\d+)', second_part)
                if pe_match:
                    spec = pe_match.group(1)
                    colon_products.append(f"PE稀释剂:1桶规格{spec}")
                
                # 查找其他产品
                other_match = re.search(r'(\d+桶规格\d+)(.*?)(PE|$)', second_part)
                if other_match:
                    other_spec = other_match.group(1)
                    other_name = other_match.group(2).strip()
                    if other_name:
                        colon_products.append(f"{other_name}:{other_spec}")
            
            products.extend(colon_products)
            
            print(f"智能分割结果:")
            for i, product in enumerate(products, 1):
                print(f"产品 {i}: {product}")
            
            return products
    
    # 默认返回原文本作为单个产品
    return [working_text]

def test_smart_split():
    """测试智能分割"""
    
    # 测试订单
    order_text = "蕊芯1Pe白底漆10桶，规格28,24-4-8 哑光银珠:1桶规格20PE稀释剂:1桶规格180"
    
    # 移除客户名称
    products = smart_split_products(order_text, "蕊芯1")
    
    print(f"\n=== 最终分割结果 ===")
    for i, product in enumerate(products, 1):
        print(f"产品 {i}: {product}")

if __name__ == "__main__":
    test_smart_split()