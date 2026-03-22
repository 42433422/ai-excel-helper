# -*- coding: utf-8 -*-
import sqlite3
import os

db_path = r'E:\FHD\XCAGI\data\app.db'
print(f'数据库路径: {db_path}')
print(f'存在: {os.path.exists(db_path)}')

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cur.fetchall()
    print('表:')
    for t in tables:
        print(f'  {t[0]}')
    conn.close()
