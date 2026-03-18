import sqlite3

# 检查七彩乐园的数据库中与"稀释剂"相关的产品
db_path = "c:/Users/97088/Desktop/新建文件夹 (4)/AI助手/unit_databases/七彩乐园.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 查询名称包含"稀释剂"或"稀料"的产品
cursor.execute("SELECT id, name, model_number FROM products WHERE name LIKE '%稀释剂%' OR name LIKE '%稀料%'")
products = cursor.fetchall()

print("=== 七彩乐园中与稀释剂相关的产品 ===\n")
for p in products:
    print(f"ID: {p[0]}, 名称: {p[1]}, 型号: {p[2]}")

conn.close()
