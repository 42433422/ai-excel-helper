# -*- coding: utf-8 -*-
import sqlite3
import sys
import os

sys.path.insert(0, r'E:\FHD\XCAGI\resources\wechat-decrypt')
from mcp_server import _decompress_content

msg_dir = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message'

wechat_id = 'wxid_tfxzqdqt87oa22'
print(f'搜索: {wechat_id}')
print()

for db_file in sorted(os.listdir(msg_dir)):
    if not db_file.endswith('.db'):
        continue
    msg_db = os.path.join(msg_dir, db_file)
    print(f'=== {db_file} ===')

    conn = sqlite3.connect(msg_db)
    cur = conn.cursor()

    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")
        tables = [r[0] for r in cur.fetchall()]

        found = 0
        for table in tables:
            try:
                cur.execute(f"SELECT message_content, WCDB_CT_message_content, create_time FROM [{table}] WHERE message_content IS NOT NULL ORDER BY create_time DESC LIMIT 100")
                rows = cur.fetchall()
                for row in rows:
                    raw = row[0]
                    ct = row[1]
                    if not raw:
                        continue
                    content = _decompress_content(raw, ct)
                    if isinstance(content, bytes):
                        content = content.decode('utf-8', errors='replace')
                    content = (content or '').strip()
                    if wechat_id in content:
                        found += 1
                        print(f'  FOUND in {table}: {content[:100]}')
            except:
                pass

        if found == 0:
            print(f'  未找到')
    except:
        pass

    conn.close()
    print()
