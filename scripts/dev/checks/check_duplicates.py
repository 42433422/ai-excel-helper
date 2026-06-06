import sqlite3

db_path = "e:/FHD/424/products.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# 查询重复产品
print("=== 查询重复的产品记录 ===")
cur.execute(
    """
    SELECT name, model_number, specification, price, COUNT(*) as cnt
    FROM products 
    WHERE model_number IN ('3721', '1870D', '8828')
    GROUP BY name, model_number, specification, price
    HAVING cnt > 1
"""
)
for row in cur.fetchall():
    print(row)

# 查询所有 3721, 1870D, 8828 的记录
print("\n=== 所有 3721, 1870D, 8828 的记录 ===")
cur.execute(
    "SELECT id, name, model_number, specification, price, is_active FROM products WHERE model_number IN ('3721', '1870D', '8828') ORDER BY model_number, specification"
)
for row in cur.fetchall():
    print(row)

conn.close()
