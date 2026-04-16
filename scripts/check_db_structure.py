import sqlite3
import os

db_files = [
    r'e:\FHD\424\半岛风情.db',
    r'e:\FHD\424\博旺家私.db',
    r'e:\FHD\424\陈鑫强.db',
]

for db_file in db_files:
    print(f'\n=== {os.path.basename(db_file)} ===')
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f'Tables: {[t[0] for t in tables]}')
        for table in tables:
            table_name = table[0]
            cursor.execute(f'PRAGMA table_info({table_name})')
            columns = cursor.fetchall()
            print(f'  {table_name}: {[c[1] for c in columns]}')
            cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
            count = cursor.fetchone()[0]
            print(f'  Rows: {count}')
            if count > 0:
                cursor.execute(f'SELECT * FROM {table_name} LIMIT 3')
                rows = cursor.fetchall()
                print(f'  Sample: {rows}')
        conn.close()
    except Exception as e:
        print(f'Error: {e}')