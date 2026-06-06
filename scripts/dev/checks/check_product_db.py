import sqlite3
from app.infrastructure.db.sync_engine import resolve_products_db_path

path = resolve_products_db_path()
print(f"数据库路径：{path}")

conn = sqlite3.connect(str(path))
cur = conn.cursor()

# 查看表结构
cur.execute("PRAGMA table_info(products)")
columns = cur.fetchall()
print("\n表结构:")
for col in columns:
    print(f"  {col[1]}: {col[2]}")

# 查看示例数据
print("\n示例数据 (前 3 条):")
cur.execute("SELECT model_number, name, specification, unit, price FROM products LIMIT 3")
rows = cur.fetchall()
for row in rows:
    print(f"  型号：{row[0]}, 名称：{row[1]}, 规格：{row[2]}, unit: {row[3]}, 价格：{row[4]}")

# 查看特定型号
print("\n特定型号数据 (3721, 1870D, 8828):")
cur.execute(
    "SELECT model_number, name, specification, unit, price FROM products WHERE model_number IN ('3721', '1870D', '8828')"
)
rows = cur.fetchall()
for row in rows:
    print(f"  型号：{row[0]}, 名称：{row[1]}, 规格：{row[2]}, unit: {row[3]}, 价格：{row[4]}")

conn.close()
