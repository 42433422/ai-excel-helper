import sqlite3

conn = sqlite3.connect('unit_databases/七彩乐园.db')
cursor = conn.cursor()

# 搜索所有哑光相关产品
sql = "SELECT model_number, name, price FROM products WHERE name LIKE '%哑光%' ORDER BY name"
cursor.execute(sql)
products = cursor.fetchall()
print('七彩乐园数据库中所有哑光相关产品:')
for p in products:
    print(f'  型号: {p[0]:15} 名称: {p[1]:40} 价格: {p[2]}')

print(f'\n共 {len(products)} 个哑光产品')

# 搜索所有白面漆产品
sql = "SELECT model_number, name, price FROM products WHERE name LIKE '%白面漆%' ORDER BY name"
cursor.execute(sql)
products = cursor.fetchall()
print('\n七彩乐园数据库中所有白面漆产品:')
for p in products:
    print(f'  型号: {p[0]:15} 名称: {p[1]:40} 价格: {p[2]}')

conn.close()
