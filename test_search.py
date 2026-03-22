# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, r'E:\FHD\XCAGI\resources\wechat-decrypt')
from mcp_server import _decompress_content

msg_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db'
import sqlite3
conn = sqlite3.connect(msg_db)
cur = conn.cursor()

table = 'Msg_89707d4abce0cecdca50a8d0718b152b'
cur.execute(f'SELECT message_content, WCDB_CT_message_content, create_time FROM [{table}] ORDER BY create_time DESC LIMIT 5')
rows = cur.fetchall()

wechat_id = 'wxid_tfxzqdqt87oa22'
found = 0
for row in rows:
    raw = row[0]
    ct = row[1]
    if not raw:
        continue
    content = _decompress_content(raw, ct)
    if isinstance(content, bytes):
        content = content.decode('utf-8', errors='replace')
    content = (content or '').strip()
    print(f'content[:100]: {content[:100] if content else "None"}')
    print(f'wechat_id in content: {wechat_id in content}')
    if wechat_id in content:
        found += 1
        print(f'FOUND! text={content[:200]}')

print(f'found: {found}')
conn.close()
