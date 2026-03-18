import sqlite3

conn = sqlite3.connect('products.db')
cursor = conn.cursor()

print("=== products.db 完整检查 ===\n")

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]
print(f"所有表: {tables}\n")

for table in tables:
    cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
    count = cursor.fetchone()[0]
    print(f"{table}: {count} 条记录")

print("\n=== customer_products 表详情 ===")
cursor.execute('SELECT * FROM customer_products LIMIT 10')
rows = cursor.fetchall()
print(f"前10条关联记录:")
for row in rows:
    print(f"  ID: {row[0]}, 单位ID: {row[1]}, 产品ID: {row[2]}, 特殊价格: {row[3]}")

print("\n=== purchase_units 表完整数据 ===")
cursor.execute('SELECT id, unit_name FROM purchase_units ORDER BY id')
units = cursor.fetchall()
print(f"共 {len(units)} 个客户单位:")
for unit in units:
    print(f"  ID {unit[0]}: {unit[1]}")

print("\n=== products 表完整数据 ===")
cursor.execute('SELECT id, name, model FROM products ORDER BY id')
products = cursor.fetchall()
print(f"共 {len(products)} 个产品:")
for p in products:
    print(f"  ID {p[0]}: {p[1]} - {p[2]}")

conn.close()
