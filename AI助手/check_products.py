import sqlite3

# 检查七彩乐园的数据库
db_path = "c:/Users/97088/Desktop/新建文件夹 (4)/AI助手/unit_databases/七彩乐园.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 查询所有产品
cursor.execute("SELECT id, name, model_number, specification FROM products")
products = cursor.fetchall()

print("=== 七彩乐园数据库中的产品 ===\n")
print(f"产品数量: {len(products)}\n")
for p in products:
    print(f"ID: {p[0]}, 名称: {p[1]}, 型号: {p[2]}, 规格: {p[3]}")

conn.close()
