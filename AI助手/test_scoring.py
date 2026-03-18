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

# 手动测试匹配逻辑
search_text = 'PE白底'
print(f'\n=== 测试匹配: "{search_text}" ===')
for product in products:
    name = product[2].lower()
    search_lower = search_text.lower()
    
    score = 0
    if search_lower in name:
        score += 60
        print(f'搜索文本在产品名中: "{search_lower}" in "{name}" (基础分数: 60)')
        
        # 漆类产品额外分数
        if any(keyword in name for keyword in ['白底漆', '白面漆', '清底漆', '清面漆', '封固底漆']):
            score += 20
            print(f'  + 漆类产品额外分数 (总分: {score})')
        else:
            print(f'  - 不是漆类产品 (总分: {score})')
    
    print(f'  最终分数: {score} - {product[1]} ({product[2]})')

conn.close()
