import sqlite3
import os

db_files = [
    r'e:\FHD\424\customer_products_final_corrected.db',
    r'e:\FHD\424\customers.db',
    r'e:\FHD\xcagi\products.db',
]

for db_file in db_files:
    print(f'\n=== {os.path.basename(db_file)} ===')
    if not os.path.exists(db_file):
        print('  文件不存在')
        continue
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f'Tables: {[t[0] for t in tables]}')
    for table in tables:
        table_name = table[0]
        cursor.execute(f'PRAGMA table_info({table_name})')
        columns = cursor.fetchall()
        print(f'  {table_name} columns: {[c[1] for c in columns]}')
        cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
        count = cursor.fetchone()[0]
        print(f'  Rows: {count}')
        if count > 0 and count <= 5:
            cursor.execute(f'SELECT * FROM {table_name}')
            rows = cursor.fetchall()
            print(f'  All rows: {rows}')
        elif count > 5:
            cursor.execute(f'SELECT * FROM {table_name} LIMIT 5')
            rows = cursor.fetchall()
            print(f'  Sample rows: {rows}')
    conn.close()