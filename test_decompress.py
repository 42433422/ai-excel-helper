# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'E:\FHD\XCAGI\resources\wechat-decrypt')
from mcp_server import _decompress_content

msg_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db'

import sqlite3
conn = sqlite3.connect(msg_db)
cur = conn.cursor()

tbl = 'Msg_89707d4abce0cecdca50a8d0718b152b'
cur.execute(f"SELECT message_content, WCDB_CT_message_content, local_id FROM [{tbl}] WHERE real_sender_id = 98")
rows = cur.fetchall()

print(f"Found {len(rows)} messages in {tbl}")
for r in rows:
    raw = r[0]
    ct = r[1]
    local_id = r[2]
    print(f"\nlocal_id={local_id}, ct={ct}")
    print(f"  raw bytes: {raw[:30] if raw else None}...")
    result = _decompress_content(raw, ct)
    print(f"  result type: {type(result)}")
    if isinstance(result, bytes):
        decoded = result.decode('utf-8', errors='replace')
        print(f"  decoded: {repr(decoded[:80])}")
    else:
        print(f"  result: {repr(result[:80]) if result else None}")

conn.close()