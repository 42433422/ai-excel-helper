import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

print('=== database.db 检查 ===')
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]
print(f'所有表: {tables}\n')

for table in tables:
    cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
    count = cursor.fetchone()[0]
    print(f'{table}: {count} 条记录')

conn.close()
