# -*- coding: utf-8 -*-
import sqlite3
import sys

sys.path.insert(0, r'E:\FHD\XCAGI\resources\wechat-decrypt')
from mcp_server import _decompress_content

msg_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db'
conn = sqlite3.connect(msg_db)
cur = conn.cursor()

table = 'Msg_302df4ea943a3f7690ce219983bc4a92'

print(f'=== 检查 {table} 表结构 ===')
cur.execute(f"PRAGMA table_info([{table}])")
cols = cur.fetchall()
print(f'字段: {[c[1] for c in cols]}')

print()
print('=== 查找 talker 包含 fxzqdqt 的消息 ===')
cur.execute(f"SELECT message_content, WCDB_CT_message_content, talker, real_sender_id, create_time FROM [{table}] WHERE talker LIKE '%fxzqdqt%' ORDER BY create_time DESC LIMIT 5")
rows = cur.fetchall()
for row in rows:
    if row[0]:
        content = _decompress_content(row[0], row[1])
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='replace')
        print(f'talker={row[2]}, real_sender_id={row[3]}')
        print(f'  {content[:200]}')
        print()

print()
print('=== 查找所有 talker ===')
cur.execute(f"SELECT DISTINCT talker FROM [{table}] LIMIT 20")
talkers = cur.fetchall()
for t in talkers:
    print(f'  {t[0]}')

conn.close()
