import sqlite3

# 检查七彩乐园数据库
conn = sqlite3.connect('unit_databases/七彩乐园.db')
cursor = conn.cursor()

print('七彩乐园数据库中的所有产品:')
print('='*80)

# 获取所有产品
cursor.execute('SELECT model_number, name, specification, price FROM products ORDER BY model_number')
products = cursor.fetchall()

for p in products:
    print(f'型号: {p[0]:15} 名称: {p[1]:30} 规格: {p[2]:10} 价格: {p[3]}')

print(f'\n共 {len(products)} 个产品')

# 搜索包含"9083"的产品
print('\n=== 搜索包含"9083"的产品 ===')
cursor.execute('SELECT model_number, name, specification, price FROM products WHERE model_number LIKE ? OR name LIKE ?', ['%9083%', '%9083%'])
results = cursor.fetchall()
if results:
    for r in results:
        print(f'型号: {r[0]:15} 名称: {r[1]:30} 规格: {r[2]:10} 价格: {r[3]}')
else:
    print('未找到包含"9083"的产品')

# 搜索包含"哑光"的产品
print('\n=== 搜索包含"哑光"的产品 ===')
cursor.execute('SELECT model_number, name, specification, price FROM products WHERE model_number LIKE ? OR name LIKE ?', ['%哑光%', '%哑光%'])
results = cursor.fetchall()
if results:
    for r in results:
        print(f'型号: {r[0]:15} 名称: {r[1]:30} 规格: {r[2]:10} 价格: {r[3]}')
else:
    print('未找到包含"哑光"的产品')

conn.close()
