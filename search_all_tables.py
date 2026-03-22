# -*- coding: utf-8 -*-
import sqlite3
import sys

sys.path.insert(0, r'E:\FHD\XCAGI\resources\wechat-decrypt')
from mcp_server import _decompress_content

msg_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db'
conn = sqlite3.connect(msg_db)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")
tables = [r[0] for r in cur.fetchall()]

target = 'wxid_tfxzqdqt87oa22'
print(f'=== 在所有表中查找包含 {target} 的消息 ===')

total_found = 0
for table in tables:
    try:
        cur.execute(f"SELECT message_content, WCDB_CT_message_content, real_sender_id, create_time FROM [{table}] ORDER BY create_time DESC LIMIT 500")
        rows = cur.fetchall()

        for row in rows:
            if row[0]:
                content = _decompress_content(row[0], row[1])
                if isinstance(content, bytes):
                    content = content.decode('utf-8', errors='replace')
                if target in content:
                    print(f'[{table}] real_sender_id={row[2]}')
                    print(f'  {content[:400]}')
                    print()
                    total_found += 1
                    break
    except Exception as e:
        pass

print(f'总共在 {total_found} 个表中找到相关消息')
conn.close()
