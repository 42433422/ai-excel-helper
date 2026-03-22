# -*- coding: utf-8 -*-
import sqlite3

db_path = r'E:\FHD\XCAGI\data\app.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print('=== wechat_contacts 表 ===')
cur.execute('SELECT id, contact_name, wechat_id, is_starred FROM wechat_contacts WHERE is_starred = 1 LIMIT 20')
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f'id={r[0]}, contact_name={r[1]}, wechat_id={r[2]}, is_starred={r[3]}')
else:
    print('没有星标联系人')
    print('查找前5条:')
    cur.execute('SELECT id, contact_name, wechat_id, is_starred FROM wechat_contacts LIMIT 5')
    for r in cur.fetchall():
        print(f'id={r[0]}, contact_name={r[1]}, wechat_id={r[2]}, is_starred={r[3]}')

conn.close()
