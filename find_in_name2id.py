# -*- coding: utf-8 -*-
import sqlite3

msg_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db'
conn = sqlite3.connect(msg_db)
cur = conn.cursor()

wechat_id = 'wxid_tfxzqdqt87oa22'

print(f'=== 在 Name2Id 中搜索 {wechat_id} ===')
cur.execute("SELECT * FROM Name2Id WHERE user_name = ?", (wechat_id,))
row = cur.fetchone()
print(f'结果: {row}')

conn.close()
