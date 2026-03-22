# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'E:\FHD\XCAGI\resources\wechat-decrypt')
from mcp_server import _decompress_content

import sqlite3
msg_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db'
conn = sqlite3.connect(msg_db)
cur = conn.cursor()

table = 'Msg_89707d4abce0cecdca50a8d0718b152b'
cur.execute(f"SELECT message_content, WCDB_CT_message_content FROM [{table}] WHERE real_sender_id = 98 ORDER BY create_time DESC LIMIT 3")
rows = cur.fetchall()

for i, row in enumerate(rows):
    raw = row[0]
    ct = row[1]
    print(f'=== 消息 {i+1} ===')
    print(f'ct (compression type): {ct}')
    print(f'raw bytes length: {len(raw) if raw else 0}')
    print(f'raw[:50]: {raw[:50] if raw else None}')

    content = _decompress_content(raw, ct)
    print(f'decompressed type: {type(content)}')
    if isinstance(content, bytes):
        print(f'decompressed bytes length: {len(content)}')
        print(f'decompressed bytes[:100]: {content[:100]}')
        try:
            text = content.decode('utf-8')
            print(f'decoded utf-8: {text[:100]}')
        except:
            try:
                text = content.decode('gbk')
                print(f'decoded gbk: {text[:100]}')
            except:
                print('decode failed')
    else:
        print(f'decompressed: {content[:100] if content else None}')
    print()

conn.close()
