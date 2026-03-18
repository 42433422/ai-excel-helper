#!/usr/bin/env python3
import sqlite3

# 直接测试智能产品匹配函数
conn = sqlite3.connect('unit_databases/七彩乐园.db')
cursor = conn.cursor()
cursor.execute('SELECT * FROM products WHERE name LIKE "%PE%" AND name LIKE "%白底%"')
products = cursor.fetchall()

print('=== 七彩乐园中的PE白底相关产品 ===')
for product in products:
    print(f'ID: {product[0]}, 型号: {product[1]}, 名称: {product[2]}')

# 手动测试修复后的匹配逻辑
search_text = 'PE白底'
print(f'\n=== 测试修复后的匹配: "{search_text}" ===')
for product in products:
    name = product[2].lower()
    search_lower = search_text.lower()
    
    score = 0
    if search_lower in name:
        base_score = 60
        print(f'搜索文本在产品名中: "{search_lower}" in "{name}" (基础分数: 60)')
        
        # 检查搜索词是否完整匹配产品名的核心部分
        if any(core in name for core in ['白底漆', '白面漆', '清底漆', '清面漆', '封固底漆']):
            # 检查产品名是否以核心词结尾（纯漆类产品）
            if name.rstrip().endswith(tuple(['白底漆', '白面漆', '清底漆', '清面漆', '封固底漆'])):
                base_score += 30  # 纯漆类产品高优先级
                print(f'  + 纯漆类产品额外分数30 (总分: {base_score})')
            elif '稀释剂' not in name and '稀料' not in name:
                base_score += 20  # 不含稀释剂的漆类产品
                print(f'  + 不含稀释剂漆类产品额外分数20 (总分: {base_score})')
            else:
                base_score += 10  # 含稀释剂的产品低优先级
                print(f'  + 含稀释剂产品额外分数10 (总分: {base_score})')
        
        score = base_score
    
    print(f'  最终分数: {score} - {product[1]} ({product[2]})')

conn.close()
