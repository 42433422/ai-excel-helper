#!/usr/bin/env python3
import sqlite3

# 直接测试七彩乐园数据库中的产品匹配
conn = sqlite3.connect('unit_databases/七彩乐园.db')
cursor = conn.cursor()
cursor.execute('SELECT * FROM products WHERE name LIKE "%PE%" AND name LIKE "%白底%"')
products = cursor.fetchall()

search_text = 'PE白底'
print(f'=== 测试匹配逻辑: "{search_text}" ===')

for product in products:
    model, name, price = product[1], product[2], product[3]
    name_lower = name.lower()
    search_lower = search_text.lower()
    
    score = 0
    if search_lower in name_lower:
        base_score = 60
        print(f'\n产品: {model} - {name}')
        print(f'  搜索词: "{search_lower}" in "{name_lower}"')
        
        # 检查搜索词是否完整匹配产品名的核心部分
        if any(core in name_lower for core in ['白底漆', '白面漆', '清底漆', '清面漆', '封固底漆']):
            print(f'  包含核心词: ✓')
            # 检查产品名是否以核心词结尾（纯漆类产品）
            if name_lower.rstrip().endswith(tuple(['白底漆', '白面漆', '清底漆', '清面漆', '封固底漆'])):
                base_score += 30  # 纯漆类产品高优先级
                print(f'  纯漆类产品 (+30): 总分 {base_score}')
            elif '稀释剂' not in name_lower and '稀料' not in name_lower:
                base_score += 20  # 不含稀释剂的漆类产品
                print(f'  不含稀释剂漆类产品 (+20): 总分 {base_score}')
            else:
                base_score += 10  # 含稀释剂的产品低优先级
                print(f'  含稀释剂产品 (+10): 总分 {base_score}')
        
        score = base_score
    
    print(f'  最终分数: {score}')

# 找出最高分的产品
best_product = max(products, key=lambda p: (search_text.lower() in p[2].lower() and 
                                           (60 + (30 if p[2].lower().rstrip().endswith(('白底漆', '白面漆', '清底漆', '清面漆', '封固底漆')) 
                                                  else 10 if '稀释剂' in p[2].lower() else 20)) or 0))

print(f'\n=== 最佳匹配结果 ===')
print(f'型号: {best_product[1]}')
print(f'名称: {best_product[2]}')
print(f'价格: {best_product[3]}')

conn.close()
