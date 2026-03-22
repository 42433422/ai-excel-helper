# -*- coding: utf-8 -*-
import sqlite3
import os

contact_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\contact\contact.db'

conn = sqlite3.connect(contact_db)
cur = conn.cursor()

print('=== 搜索包含 wxid 的联系人 ===')
cur.execute("SELECT id, username, nick_name, remark FROM contact WHERE username LIKE 'wxid%' LIMIT 20")
rows = cur.fetchall()
for r in rows:
    print(f'  id: {r[0]}, username: {r[1]}, nick_name: {r[2]}, remark: {r[3]}')

conn.close()
