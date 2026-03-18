import sqlite3
conn = sqlite3.connect('products.db')
cur = conn.cursor()

# 获取所有表
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cur.fetchall()
print("=== 数据库中的所有表 ===")
for t in tables:
    print(f"  - {t[0]}")

# 检查每个表的列信息
print("\n=== 表结构详情 ===")
for t in tables:
    table_name = t[0]
    cur.execute(f"PRAGMA table_info({table_name})")
    cols = cur.fetchall()
    print(f"\n表 {table_name}:")
    for col in cols:
        print(f"  {col[1]} ({col[2]})")

conn.close()
