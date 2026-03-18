#!/usr/bin/env python3
import sqlite3
import os

# 直接模拟AI解析器中的匹配逻辑
print("=== 模拟AI解析器匹配过程 ===")

# 连接到七彩乐园数据库
conn = sqlite3.connect('unit_databases/七彩乐园.db')
cursor = conn.cursor()
cursor.execute('SELECT * FROM products WHERE name LIKE "%PE%" AND name LIKE "%白底%"')
products = cursor.fetchall()

search_text = 'PE白底'
print(f"搜索文本: {search_text}")
print(f"找到 {len(products)} 个产品:")

# 模拟AI解析器的匹配过程
for i, product in enumerate(products):
    model, name, price = product[1], product[2], product[3]
    print(f"\n产品 {i+1}: {model} - {name}")
    
    # 传统解析匹配
    search_lower = search_text.lower()
    name_lower = name.lower()
    
    score = 0
    
    if search_lower == name_lower:
        score += 80
        print(f"  精确匹配: {score}")
    elif search_lower in name_lower:
        base_score = 60
        print(f"  搜索词在产品名中: 基础分数 {base_score}")
        
        # 检查搜索词是否完整匹配产品名的核心部分
        core_keywords = ['白底漆', '白面漆', '清底漆', '清面漆', '封固底漆']
        if any(core in name_lower for core in core_keywords):
            print(f"  包含核心词: {core_keywords}")
            # 检查产品名是否以核心词结尾（纯漆类产品）
            if name_lower.rstrip().endswith(tuple(core_keywords)):
                base_score += 30  # 纯漆类产品高优先级
                print(f"  纯漆类产品 (+30): 总分 {base_score}")
            elif '稀释剂' not in name_lower and '稀料' not in name_lower:
                base_score += 20  # 不含稀释剂的漆类产品
                print(f"  不含稀释剂漆类产品 (+20): 总分 {base_score}")
            else:
                base_score += 10  # 含稀释剂的产品低优先级
                print(f"  含稀释剂产品 (+10): 总分 {base_score}")
        
        score += base_score
        print(f"  最终分数: {score}")
    
    # 其他匹配逻辑...
    
    print(f"  传统解析得分: {score}")

# 找出最高分的产品
best_score = 0
best_product = None
for product in products:
    model, name = product[1], product[2]
    search_lower = search_text.lower()
    name_lower = name.lower()
    
    score = 0
    if search_lower in name_lower:
        base_score = 60
        core_keywords = ['白底漆', '白面漆', '清底漆', '清面漆', '封固底漆']
        if any(core in name_lower for core in core_keywords):
            if name_lower.rstrip().endswith(tuple(core_keywords)):
                base_score += 30
            elif '稀释剂' not in name_lower and '稀料' not in name_lower:
                base_score += 20
            else:
                base_score += 10
        score = base_score
    
    if score > best_score:
        best_score = score
        best_product = product

print(f"\n=== 最佳匹配结果 ===")
if best_product:
    print(f"型号: {best_product[1]}")
    print(f"名称: {best_product[2]}")
    print(f"分数: {best_score}")
else:
    print("未找到匹配产品")

conn.close()
