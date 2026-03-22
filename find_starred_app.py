# -*- coding: utf-8 -*-
import sqlite3

db = r'E:\FHD\XCAGI\data\app.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

print('=== 查找星标联系人 ===')
cur.execute('SELECT id, contact_name, wechat_id, is_starred FROM wechat_contact WHERE is_starred = 1 LIMIT 20')
rows = cur.fetchall()
for r in rows:
    print(f'id={r[0]}, contact_name={r[1]}, wechat_id={r[2]}, is_starred={r[3]}')

if not rows:
    print('没有星标联系人，查找所有:')
    cur.execute('SELECT id, contact_name, wechat_id, is_starred FROM wechat_contact LIMIT 10')
    for r in cur.fetchall():
        print(f'id={r[0]}, contact_name={r[1]}, wechat_id={r[2]}, is_starred={r[3]}')

conn.close()
