# -*- coding: utf-8 -*-
import sqlite3
import sys

sys.path.insert(0, r'E:\FHD\XCAGI\resources\wechat-decrypt')

msg_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db'
conn = sqlite3.connect(msg_db)
cur = conn.cursor()

print('=== 当前微信用户消息样本 ===')
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%' LIMIT 1")
table = cur.fetchone()[0]

cur.execute(f"SELECT message_content, WCDB_CT_message_content, real_sender_id, create_time FROM [{table}] ORDER BY create_time DESC LIMIT 50")
rows = cur.fetchall()

from mcp_server import _decompress_content

for row in rows:
    if row[0]:
        content = _decompress_content(row[0], row[1])
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='replace')
        # 检查是否包含当前用户 wxid
        if 'wxid_bommxleja9kq22' in content or 'bommxleja9kq22' in content:
            print(f'real_sender_id={row[2]}')
            print(f'  {content[:400]}')
            print()

conn.close()
