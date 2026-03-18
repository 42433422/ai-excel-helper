#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复产品分割逻辑
"""

import re

def improved_split_products(text: str, purchase_unit: str) -> list:
    """改进的产品分割逻辑"""
    
    # 移除购买单位
    working_text = text
    if purchase_unit:
        working_text = working_text.replace(purchase_unit, "").strip()
    
    print(f"=== 改进的产品分割测试 ===")
    print(f"原始文本: {text}")
    print(f"移除客户后: {working_text}")
    
    products = []
    
    # 特殊处理这个复杂格式
    # `Pe白底漆10桶，规格28KGPE稀释剂:1桶，规格180KG`
    
    # 按逗号分割
    comma_parts = working_text.split('，')
    
    for i, part in enumerate(comma_parts):
        part = part.strip()
        if not part:
            continue
            
        print(f"\n处理逗号部分 {i+1}: '{part}'")
        
        # 查找规格信息
        spec_matches = list(re.finditer(r'规格(\d+)', part))
        
        if spec_matches:
            # 这个部分包含规格信息
            spec_info = spec_matches[-1].group(0)  # 最后一个规格
            spec_value = spec_matches[-1].group(1)
            
            # 查找前面的内容
            before_spec = part[:spec_matches[-1].start()].strip()
            after_spec = part[spec_matches[-1].end():].strip()
            
            print(f"  规格: {spec_info}")
            print(f"  规格前: '{before_spec}'")
            print(f"  规格后: '{after_spec}'")
            
            # 如果规格前的内容包含产品信息
            if before_spec:
                # 检查是否包含"PE"（可能是另一个产品的开始）
                if 'PE' in before_spec and ':' in before_spec:
                    # 这是一个完整的产品信息
                    products.append(part)
                    print(f"  ✅ 完整产品: {part}")
                else:
                    # 这是一个产品+规格
                    products.append(part)
                    print(f"  ✅ 产品+规格: {part}")
            elif after_spec:
                # 只有规格+其他内容
                # 检查是否是另一个产品
                if after_spec.startswith('PE'):
                    # 这是下一个产品的开始
                    # 构建完整的产品信息
                    full_product = after_spec
                    
                    # 查找下一个规格
                    next_spec_match = re.search(r'规格(\d+)', working_text, re.search(f'规格{after_spec}', working_text).start() + len(after_spec) if re.search(f'规格{after_spec}', working_text) else -1)
                    if next_spec_match:
                        full_product += f"，规格{next_spec_match.group(1)}"
                    
                    products.append(full_product)
                    print(f"  ✅ 另一个产品: {full_product}")
                else:
                    # 规格后的其他信息
                    products.append(part)
                    print(f"  ✅ 规格+其他: {part}")
        else:
            # 这个部分不包含规格
            products.append(part)
            print(f"  ✅ 直接添加: {part}")
    
    # 合并相邻的产品信息
    final_products = []
    i = 0
    while i < len(products):
        current = products[i]
        
        # 检查是否需要与下一个合并
        if i + 1 < len(products):
            next_product = products[i + 1]
            
            # 如果当前以"规格数字"结尾，下一个以"PE"开头
            if re.search(r'规格\d+$', current) and next_product.startswith('PE'):
                # 合并它们
                merged = current + "，" + next_product
                final_products.append(merged)
                print(f"  🔄 合并产品: {current} + {next_product} = {merged}")
                i += 2  # 跳过下一个
                continue
        
        final_products.append(current)
        i += 1
    
    print(f"\n=== 最终分割结果 ===")
    for i, product in enumerate(final_products, 1):
        print(f"产品 {i}: {product}")
    
    return final_products

def test_improved_split():
    """测试改进的分割逻辑"""
    
    # 测试订单
    order_text = "蕊芯Pe白底漆10桶，规格28KGPE稀释剂:1桶，规格180KG"
    
    products = improved_split_products(order_text, "蕊芯家私")
    
    return products

if __name__ == "__main__":
    test_improved_split()