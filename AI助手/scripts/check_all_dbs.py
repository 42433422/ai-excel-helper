import sqlite3
import os

print("=== 检查所有数据库 ===\n")

# 检查 products.db
print("1. products.db:")
db_path = 'products.db'
print(f"   路径: {os.path.abspath(db_path)}")
print(f"   存在: {os.path.exists(db_path)}")
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cursor.fetchall()]
    print(f"   表: {tables}")
    if 'purchase_units' in tables:
        cursor.execute('SELECT COUNT(*) FROM purchase_units')
        print(f"   purchase_units 记录数: {cursor.fetchone()[0]}")
    conn.close()

# 检查 database.db
print("\n2. database.db:")
db_path = 'database.db'
print(f"   路径: {os.path.abspath(db_path)}")
print(f"   存在: {os.path.exists(db_path)}")
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cursor.fetchall()]
    print(f"   表: {tables}")
    conn.close()

print(f"\n当前工作目录: {os.getcwd()}")
