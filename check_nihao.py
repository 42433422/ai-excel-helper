# -*- coding: utf-8 -*-
import sys
import os

sys.path.insert(0, r'E:\FHD\XCAGI\resources\wechat-decrypt')
from mcp_server import _decompress_content

msg_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db'
import sqlite3

conn = sqlite3.connect(msg_db)
cur = conn.cursor()

tbl = 'Msg_89707d4abce0cecdca50a8d0718b152b'
cur.execute(f"SELECT message_content, WCDB_CT_message_content, real_sender_id, local_id FROM [{tbl}] WHERE real_sender_id = 98")
rows = cur.fetchall()

print(f"Table {tbl} has {len(rows)} messages for sender_id=98:")
for r in rows:
    raw, ct, sender, local_id = r
    content = _decompress_content(raw, ct) if raw else ""
    if isinstance(content, bytes):
        content = content.decode('utf-8', errors='replace')
    print(f"\n  local_id={local_id}, ct={ct}:")
    print(f"    {repr(content[:100]) if content else 'None'}")

conn.close()