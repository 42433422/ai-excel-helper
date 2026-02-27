import sqlite3
import os
import sys

# 模拟Flask应用的环境
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DATA_DIR = BASE_DIR

def get_db_path():
    """获取数据库路径（兼容PyInstaller打包）"""
    if hasattr(sys, '_MEIPASS'):
        db_path = os.path.join(APP_DATA_DIR, 'products.db')
    else:
        db_path = os.path.join(BASE_DIR, 'products.db')
    return db_path

db_path = get_db_path()
print(f"数据库路径: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 查看所有订单号
cursor.execute("SELECT order_number, status, created_at FROM orders ORDER BY created_at DESC LIMIT 10")
orders = cursor.fetchall()

print("\n最近的10个订单:")
for order in orders:
    print(f"  {order[0]} | {order[1]} | {order[2]}")

# 检查是否有重复的26-02-00000A
cursor.execute("SELECT COUNT(*) FROM orders WHERE order_number = '26-02-00000A'")
count = cursor.fetchone()[0]
print(f"\n订单号 26-02-00000A 的数量: {count}")

conn.close()
