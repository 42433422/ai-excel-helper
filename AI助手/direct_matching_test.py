#!/usr/bin/env python3
import sqlite3
import os
import sys

# 直接模拟传统匹配逻辑
print("=== 直接模拟传统匹配逻辑 ===")

# 连接到七彩乐园数据库
conn = sqlite3.connect('unit_databases/七彩乐园.db')
cursor = conn.cursor()
cursor.execute('SELECT * FROM products WHERE name LIKE "%PE%" AND name LIKE "%白底%"')
products = cursor.fetchall()

search_text = 'PE白底'
print(f"搜索文本: {search_text}")
print(f"找到 {len(products)} 个产品:")

# 执行传统匹配逻辑
for i, product in enumerate(products):
    model, name, price = product[1], product[2], product[3]
    print(f"\n产品 {i+1}: {model} - {name}")
    
    # 执行匹配逻辑
    search_lower = search_text.lower()
    name_lower = name.lower()
    
    score = 0
    print(f"搜索: '{search_lower}' vs 产品: '{name_lower}'")
    
    # 1. 精确匹配
    if search_lower == name_lower:
        score += 80
        print(f"  精确匹配: {score}")
    elif search_lower in name_lower:
        print(f"  包含匹配: 搜索词在产品名中")
        # 检查搜索词是否完整匹配产品名的核心部分
        if any(core in name_lower for core in ['白底漆', '白面漆', '清底漆', '清面漆', '封固底漆']):
            print(f"  包含核心词: ✓")
            # 优先级逻辑：纯漆类产品 > 含稀释剂产品
            if name_lower.rstrip().endswith(tuple(['白底漆', '白面漆', '清底漆', '清面漆', '封固底漆'])):
                score += 90  # 纯漆类产品高优先级
                print(f"  纯漆类产品 (+90): 总分 {score}")
            elif '稀释剂' not in name_lower and '稀料' not in name_lower:
                score += 80  # 不含稀释剂的漆类产品
                print(f"  不含稀释剂漆类产品 (+80): 总分 {score}")
            else:
                score += 70  # 含稀释剂的产品低优先级
                print(f"  含稀释剂产品 (+70): 总分 {score}")
        else:
            score += 60  # 基础匹配分数
            print(f"  基础匹配 (+60): 总分 {score}")
    else:
        score += 20  # 包含匹配
        print(f"  其他匹配 (+20): 总分 {score}")
    
    print(f"  最终分数: {score}")

# 找出最佳匹配
best_score = 0
best_product = None
for product in products:
    model, name = product[1], product[2]
    search_lower = search_text.lower()
    name_lower = name.lower()
    
    score = 0
    if search_lower in name_lower:
        if any(core in name_lower for core in ['白底漆', '白面漆', '清底漆', '清面漆', '封固底漆']):
            if name_lower.rstrip().endswith(tuple(['白底漆', '白面漆', '清底漆', '清面漆', '封固底漆'])):
                score = 90
            elif '稀释剂' not in name_lower and '稀料' not in name_lower:
                score = 80
            else:
                score = 70
        else:
            score = 60
    
    if score > best_score:
        best_score = score
        best_product = product

print(f"\n=== 最佳匹配结果 ===")
if best_product:
    print(f"型号: {best_product[1]}")
    print(f"名称: {best_product[2]}")
    print(f"价格: {best_product[3]}")
    print(f"分数: {best_score}")
else:
    print("未找到匹配产品")

conn.close()
