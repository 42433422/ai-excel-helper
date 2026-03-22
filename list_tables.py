# -*- coding: utf-8 -*-
import sqlite3

db_path = r'E:\FHD\XCAGI\data\app.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print('=== 所有表 ===')
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
for t in tables:
    print(f'  {t[0]}')

conn.close()
