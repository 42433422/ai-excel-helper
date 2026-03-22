# -*- coding: utf-8 -*-
import sqlite3

db_path = r'E:\FHD\XCAGI\app.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print('=== 所有表 ===')
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
for t in tables:
    print(f'  {t[0]}')

print()
print('=== wechat_contacts 表 ===')
cur.execute('SELECT id, contact_name, wechat_id, is_starred FROM wechat_contacts LIMIT 20')
rows = cur.fetchall()
for r in rows:
    print(f'id={r[0]}, contact_name={r[1]}, wechat_id={r[2]}, is_starred={r[3]}')

conn.close()
