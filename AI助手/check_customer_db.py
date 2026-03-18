import sqlite3
import os

# 检查客户产品数据库
db_path = 'unit_databases/蕊芯家私.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print('=== 检查蕊芯家私的产品数据库 ===')

# 获取表结构
cursor.execute('PRAGMA table_info(products)')
columns = cursor.fetchall()
print('表结构:')
for col in columns:
    print('  -', col[1], col[2])

print()

# 获取所有产品
cursor.execute('SELECT * FROM products')
products = cursor.fetchall()
print(f'产品数量: {len(products)}')
print('产品列表:')
for i, product in enumerate(products, 1):
    print(f'  {i}. {product[2]}')  # name 字段

print()

# 查找包含PE的产品
cursor.execute('SELECT * FROM products WHERE name LIKE ?', ('%PE%',))
pe_products = cursor.fetchall()
print('包含PE的产品:')
if pe_products:
    for product in pe_products:
        print('  -', product[2])  # name 字段
else:
    print('  ❌ 未找到包含PE的产品')

print()

# 查找包含稀释剂的产品
cursor.execute('SELECT * FROM products WHERE name LIKE ?', ('%稀释剂%',))
thinner_products = cursor.fetchall()
print('包含稀释剂的产品:')
if thinner_products:
    for product in thinner_products:
        print('  -', product[2])  # name 字段
else:
    print('  ❌ 未找到包含稀释剂的产品')

print()

# 查找包含白底的产品
cursor.execute('SELECT * FROM products WHERE name LIKE ?', ('%白底%',))
primer_products = cursor.fetchall()
print('包含白底的产品:')
if primer_products:
    for product in primer_products:
        print('  -', product[2])  # name 字段
else:
    print('  ❌ 未找到包含白底的产品')

print()

# 查找包含PU的产品
cursor.execute('SELECT * FROM products WHERE name LIKE ?', ('%PU%',))
pu_products = cursor.fetchall()
print('包含PU的产品:')
if pu_products:
    for product in pu_products:
        print('  -', product[2])  # name 字段
else:
    print('  ❌ 未找到包含PU的产品')

conn.close()