# -*- coding: utf-8 -*-
import json
import sqlite3
import sys

sys.path.insert(0, r'E:\FHD\XCAGI\resources\wechat-decrypt')
from mcp_server import _decompress_content

msg_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db'
conn = sqlite3.connect(msg_db)
cur = conn.cursor()

table = 'Msg_89707d4abce0cecdca50a8d0718b152b'
cur.execute(f"SELECT message_content, WCDB_CT_message_content FROM [{table}] WHERE real_sender_id = 98 ORDER BY create_time DESC LIMIT 3")
rows = cur.fetchall()

messages = []
for row in rows:
    raw = row[0]
    ct = row[1]
    if not raw:
        continue
    content = _decompress_content(raw, ct)
    if isinstance(content, bytes):
        content = content.decode('utf-8', errors='replace') if content else ''
    content = (content or "").strip()
    if content:
        messages.append({"role": "other", "text": content})
    print(f'Added: {content[:50]}...')

print()
print(f'Total messages: {len(messages)}')
print(f'JSON: {json.dumps(messages, ensure_ascii=False)[:500]}')

conn.close()
