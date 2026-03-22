# -*- coding: utf-8 -*-
import sqlite3
import sys

sys.path.insert(0, r'E:\FHD\XCAGI\resources\wechat-decrypt')
from mcp_server import _decompress_content

msg_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\biz_message_0.db'
conn = sqlite3.connect(msg_db)
cur = conn.cursor()

print('=== biz_message_0.db 表结构 ===')
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print(f'表: {[t[0] for t in tables]}')

if tables:
    table = tables[0][0]
    cur.execute(f"PRAGMA table_info([{table}])")
    cols = cur.fetchall()
    print(f'字段: {[c[1] for c in cols]}')
    print()
    print('=== 消息样本 ===')
    cur.execute(f"SELECT message_content, WCDB_CT_message_content, create_time FROM [{table}] ORDER BY create_time DESC LIMIT 5")
    rows = cur.fetchall()
    for row in rows:
        if row[0]:
            content = _decompress_content(row[0], row[1])
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='replace')
            print(f'time={row[2]}')
            print(f'  {content[:300]}')
            print()

conn.close()
