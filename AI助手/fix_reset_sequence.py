import sqlite3
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DATA_DIR = BASE_DIR

def get_db_path():
    if hasattr(sys, '_MEIPASS'):
        db_path = os.path.join(APP_DATA_DIR, 'products.db')
    else:
        db_path = os.path.join(BASE_DIR, 'products.db')
    return db_path

db_path = get_db_path()
print(f"数据库路径: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 删除重置记录
cursor.execute("DELETE FROM orders WHERE order_number = '26-02-00000A'")
deleted = cursor.rowcount
conn.commit()

print(f"已删除 {deleted} 条重置记录")

conn.close()
print("完成！")
