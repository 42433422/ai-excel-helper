import sqlite3

db_path = r'C:\Users\Administrator\Desktop\新建文件夹 (4)\AI助手\products.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(orders)")
columns = cursor.fetchall()
print("Orders table columns:")
for col in columns:
    print(f"  {col}")

conn.close()
