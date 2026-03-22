# -*- coding: utf-8 -*-
import sqlite3
import os

msg_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db'
contact_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\contact\contact.db'

conn = sqlite3.connect(msg_db)
cur = conn.cursor()

# 1. 获取第一个消息表的结构和样本
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")
tables = [r[0] for r in cur.fetchall()]
table = tables[0]

cur.execute(f"SELECT * FROM [{table}] WHERE real_sender_id = 3 LIMIT 1")
row = cur.fetchone()
print(f'样本消息 (real_sender_id=3): {row}')
print()

# 2. 查看 contact 表结构
print('=== contact 表结构 ===')
conn2 = sqlite3.connect(contact_db)
cur2 = conn2.cursor()
cur2.execute("SELECT name FROM sqlite_master WHERE type='table'")
ctables = [r[0] for r in cur2.fetchall()]
print(f'表: {ctables}')

cur2.execute("PRAGMA table_info([contact])")
cols = cur2.fetchall()
print(f'contact 表字段: {[c[1] for c in cols]}')
print()

# 3. 查找包含 wxid 的记录
print('=== 搜索包含 wxid 的联系人 ===')
cur2.execute("SELECT UserName, NickName, Remark FROM [contact] WHERE UserName LIKE 'wxid%' LIMIT 10")
rows = cur2.fetchall()
for r in rows:
    print(f'  UserName: {r[0]}, NickName: {r[1]}, Remark: {r[2]}')

conn.close()
conn2.close()
