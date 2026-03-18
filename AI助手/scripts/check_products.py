import sqlite3

conn = sqlite3.connect('products.db')
cursor = conn.cursor()

print("=== products.db 数据库检查 ===\n")

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]
print(f"所有表: {tables}\n")

if 'products' in tables:
    cursor.execute('SELECT COUNT(*) FROM products')
    count = cursor.fetchone()[0]
    print(f"products 表记录数: {count}")
    
    cursor.execute('SELECT * FROM products LIMIT 5')
    rows = cursor.fetchall()
    print(f"\n前5条产品记录:")
    for row in rows:
        print(f"  ID: {row[0]}, 名称: {row[1]}, 型号: {row[2]}")

if 'purchase_units' in tables:
    cursor.execute('SELECT COUNT(*) FROM purchase_units')
    count = cursor.fetchone()[0]
    print(f"\npurchase_units 表记录数: {count}")
    
    cursor.execute('SELECT * FROM purchase_units LIMIT 5')
    rows = cursor.fetchall()
    print(f"\n前5条客户单位记录:")
    for row in rows:
        print(f"  ID: {row[0]}, 名称: {row[1]}")

conn.close()
