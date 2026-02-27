import sqlite3

# 检查原始数据库
conn = sqlite3.connect('products.db')
cursor = conn.cursor()

# 列出所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tables in products.db:", tables)

# 检查purchase_units表
cursor.execute("SELECT COUNT(*) FROM purchase_units")
count = cursor.fetchone()
print("purchase_units count:", count)

conn.close()

# 检查database.db
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("\nTables in database.db:", tables)

conn.close()
