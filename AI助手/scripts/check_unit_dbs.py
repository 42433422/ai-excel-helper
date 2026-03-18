import sqlite3
import os

print("=== 检查各客户单位数据库 ===\n")

unit_dir = 'unit_databases'
for db_file in os.listdir(unit_dir):
    if db_file.endswith('.db'):
        db_path = os.path.join(unit_dir, db_file)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cursor.fetchall()]
        
        if 'products' in tables:
            cursor.execute('SELECT COUNT(*) FROM products')
            count = cursor.fetchone()[0]
            print(f"{db_file}: products = {count} 条")
        
        conn.close()
