# -*- coding: utf-8 -*-
import sqlite3

contact_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\contact\contact.db'
conn = sqlite3.connect(contact_db)
cur = conn.cursor()

target = 'wxid_tfxzqdqt87oa22'
print(f'=== 查找 {target} ===')
cur.execute("SELECT id, username, nick_name FROM contact WHERE username = ?", (target,))
rows = cur.fetchall()
for r in rows:
    print(f'id={r[0]}, username={r[1]}, nick_name={r[2]}')

conn.close()
