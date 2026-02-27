import sqlite3

conn = sqlite3.connect('products.db')
cursor = conn.cursor()

cursor.execute('PRAGMA table_info(purchase_units)')
columns = cursor.fetchall()
print('purchase_units table columns:')
for col in columns:
    print(f'  {col}')

cursor.execute('SELECT * FROM purchase_units LIMIT 5')
rows = cursor.fetchall()
print(f'\nTotal records: {cursor.execute("SELECT COUNT(*) FROM purchase_units").fetchone()[0]}')
print('\nSample data:')
for row in rows:
    print(f'  {row}')

conn.close()
