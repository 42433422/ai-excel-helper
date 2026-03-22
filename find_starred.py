# -*- coding: utf-8 -*-
import sqlite3

db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\contact\contact.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

print('=== 查找星标联系人 ===')
cur.execute('SELECT id, username, nick_name, remark FROM contact WHERE username LIKE "wxid%" LIMIT 20')
for r in cur.fetchall():
    print(f'id={r[0]}, username={r[1]}, nick_name={r[2]}, remark={r[3]}')

conn.close()
