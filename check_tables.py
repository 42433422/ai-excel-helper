import sqlite3
conn = sqlite3.connect('products.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'ai_%'")
print([r[0] for r in cursor.fetchall()])
