import sqlite3

conn = sqlite3.connect('unit_databases/七彩乐园.db')
cursor = conn.cursor()

# 搜索哑光白面漆相关产品
sql = "SELECT model_number, name, price FROM products WHERE name LIKE '%哑光%' AND name LIKE '%白面漆%' ORDER BY name"
cursor.execute(sql)
products = cursor.fetchall()
print('七彩乐园数据库中的哑光白面漆产品:')
for p in products:
    print(f'  型号: {p[0]:15} 名称: {p[1]:30} 价格: {p[2]}')

conn.close()
