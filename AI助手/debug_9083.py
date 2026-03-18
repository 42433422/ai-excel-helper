from shipment_parser import ShipmentParser
import sqlite3

# 测试9083的匹配过程
order_text = '七彩乐园10桶9083规格28'

parser = ShipmentParser()

# 手动测试容错匹配
print('=== 测试9083的容错匹配 ===')
conn = sqlite3.connect('unit_databases/七彩乐园.db')
cursor = conn.cursor()

# 测试9083的查询
keyword = '9083'
print(f'测试关键词: {keyword}')

# 1. 精确匹配
cursor.execute('''
    SELECT p.model_number, p.name
    FROM products p
    WHERE UPPER(p.model_number) = UPPER(?)
    LIMIT 1
''', [keyword])
exact_result = cursor.fetchone()
print(f'精确匹配结果: {exact_result}')

# 2. 容错匹配
cursor.execute('''
    SELECT p.model_number, p.name
    FROM products p
    WHERE (UPPER(p.model_number) LIKE UPPER(?) OR UPPER(p.model_number) LIKE UPPER(?))
    ORDER BY p.model_number
    LIMIT 3
''', [f'{keyword[0:2]}%', f'{keyword[0:3]}%'])  # 取关键词前2-3位作为匹配前缀
fuzzy_results = cursor.fetchall()
print(f'容错匹配结果:')
for r in fuzzy_results:
    print(f'  {r[0]} - {r[1]}')

conn.close()

# 3. 测试解析器匹配
print('\n=== 测试解析器匹配 ===')
result = parser._match_product_from_db('10桶9083规格28', '七彩乐园', number_mode=True)
print('解析器匹配结果:', result)
