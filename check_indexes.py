import sqlite3
conn = sqlite3.connect('products.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
indexes = [r[0] for r in cur.fetchall()]
print("当前数据库索引:", indexes)

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("当前数据库表:", tables)
conn.close()
