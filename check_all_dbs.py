# -*- coding: utf-8 -*-
import sqlite3
import os

files = ['app.db', 'customers.db', 'products.db', 'users.db']
for f in files:
    path = os.path.join(r'E:\FHD\XCAGI', f)
    if os.path.exists(path):
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        print(f'{f}: {tables}')
        conn.close()
