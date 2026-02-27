#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析并改进新的订单格式处理
"""

import re

def analyze_new_order_format():
    """分析新订单格式"""
    
    order_text = "蕊芯Pe白底漆10桶，规格28KGPE稀释剂:1桶，规格180KG"
    
    print("=== 分析新订单格式 ===")
    print(f"订单: {order_text}")
    print()
    
    # 移除客户名称
    text = order_text.replace("蕊芯", "").strip()
    print(f"移除客户后: {text}")
    
    # 分析产品分割
    print("\n=== 产品分割分析 ===")
    
    # 查找所有可能的分隔点
    print("查找逗号分隔:")
    comma_parts = text.split('，')
    for i, part in enumerate(comma_parts):
        print(f"  逗号分割 {i+1}: '{part}'")
    
    # 查找"桶"位置，这可能是产品分界点
    print("\n查找桶分隔:")
    tin_positions = [i for i, c in enumerate(text) if c == '桶']
    print(f"桶位置: {tin_positions}")
    
    # 分析第一个逗号后的内容
    comma_pos = text.find('，')
    if comma_pos > 0:
        first_part = text[:comma_pos]  # "Pe白底漆10桶"
        second_part = text[comma_pos+1:]  # "规格28KGPE稀释剂:1桶，规格180KG"
        
        print(f"\n第一部分: {first_part}")
        print(f"第二部分: {second_part}")
        
        # 分析第二部分
        print("\n分析第二部分:")
        
        # 查找"规格"后的数字
        spec_matches = list(re.finditer(r'规格(\d+)', second_part))
        print(f"规格匹配: {[m.group(0) for m in spec_matches]}")
        
        # 查找"PE"位置，这可能是另一个产品的开始
        pe_position = second_part.find('PE')
        if pe_position > 0:
            pe_part = second_part[pe_position:]  # 从PE开始的所有内容
            print(f"PE部分: {pe_part}")
            
            # 手动分割PE部分
            if ':' in pe_part:
                pe_items = pe_part.split(',')
                for item in pe_items:
                    print(f"  PE分割项: {item.strip()}")
    
    print("\n=== 手动分割结果 ===")
    # 手动正确的分割应该是：
    # 1. Pe白底漆10桶，规格28KG
    # 2. PE稀释剂:1桶，规格180KG
    
    manual_split = [
        "Pe白底漆10桶，规格28KG",
        "PE稀释剂:1桶，规格180KG"
    ]
    
    for i, product in enumerate(manual_split, 1):
        print(f"产品 {i}: {product}")
    
    print("\n=== 客户匹配分析 ===")
    # 检查为什么匹配到"蕊芯"而不是"蕊芯家私"
    print("数据库中的蕊芯客户:")
    import sqlite3
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, unit_name FROM purchase_units WHERE unit_name LIKE '%蕊芯%' ORDER BY id")
    customers = cursor.fetchall()
    for customer in customers:
        print(f"  ID {customer[0]}: {customer[1]}")
    
    conn.close()
    
    print("\n匹配逻辑问题:")
    print("当前逻辑: 特殊处理'蕊芯1' -> '蕊芯家私1'")
    print("但在这个订单中，只有'蕊芯'，没有'1'")
    print("需要添加: '蕊芯' -> '蕊芯家私' 的匹配")

if __name__ == "__main__":
    analyze_new_order_format()