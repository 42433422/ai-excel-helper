import sqlite3
import os

db_path = r'C:\Users\Administrator\Desktop\新建文件夹 (4)\AI助手\products.db'
print(f"Database exists: {os.path.exists(db_path)}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]
print(f"Tables in products.db: {tables}")

if 'orders' in tables:
    cursor.execute("SELECT COUNT(*) FROM orders")
    count = cursor.fetchone()[0]
    print(f"Orders count: {count}")
    
    cursor.execute("SELECT order_number, created_at FROM orders ORDER BY created_at DESC LIMIT 3")
    orders = cursor.fetchall()
    print(f"Latest orders: {orders}")
else:
    print("orders table NOT FOUND!")

conn.close()
