# -*- coding: utf-8 -*-
import sqlite3
import sys

sys.path.insert(0, r'E:\FHD\XCAGI\resources\wechat-decrypt')
from mcp_server import _decompress_content

msg_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db'
conn = sqlite3.connect(msg_db)
cur = conn.cursor()

print('=== 在 Msg_89707d4abce0cecdca50a8d0718b152b 中搜索印记的所有消息 ===')

table = 'Msg_89707d4abce0cecdca50a8d0718b152b'
cur.execute(f"SELECT message_content, WCDB_CT_message_content, real_sender_id, create_time FROM [{table}] WHERE real_sender_id = 98 ORDER BY create_time DESC LIMIT 20")
rows = cur.fetchall()

for row in rows:
    if row[0]:
        content = _decompress_content(row[0], row[1])
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='replace')
        print(f'time={row[3]}, len={len(content)}')
        print(f'  {content[:500]}')
        print()

conn.close()
