import sqlite3
conn = sqlite3.connect('e:/FHD/AI助手/products.db')
cur = conn.cursor()

# 获取所有表
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cur.fetchall()
print("=== AI助手 products.db 中的所有表 ===")
for t in tables:
    print(f"  - {t[0]}")

# 检查索引
cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
indexes = cur.fetchall()
print("\n=== 数据库索引 ===")
for idx in indexes:
    print(f"  - {idx[0]}")

conn.close()
