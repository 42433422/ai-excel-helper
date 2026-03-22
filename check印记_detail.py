# -*- coding: utf-8 -*-
import sqlite3

contact_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\contact\contact.db'
conn = sqlite3.connect(contact_db)
cur = conn.cursor()

print('=== 印记联系人详细信息 ===')
cur.execute("SELECT * FROM contact WHERE username = 'wxid_tfxzqdqt87oa22'")
rows = cur.fetchall()
if rows:
    cur.execute("PRAGMA table_info(contact)")
    cols = [c[1] for c in cur.fetchall()]
    print(f'字段: {cols}')
    for r in rows:
        for i, col in enumerate(cols):
            print(f'  {col}: {r[i]}')
else:
    print('未找到')
    # 模糊搜索
    cur.execute("SELECT id, username, nick_name, remark FROM contact WHERE nick_name LIKE '%印记%' OR remark LIKE '%印记%'")
    for r in cur.fetchall():
        print(f'  id={r[0]}, username={r[1]}, nick_name={r[2]}, remark={r[3]}')

conn.close()
