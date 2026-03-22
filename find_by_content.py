# -*- coding: utf-8 -*-
import sqlite3
import sys

sys.path.insert(0, r'E:\FHD\XCAGI\resources\wechat-decrypt')
from mcp_server import _decompress_content

msg_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db'
conn = sqlite3.connect(msg_db)
cur = conn.cursor()

table = 'Msg_302df4ea943a3f7690ce219983bc4a92'
target = '印记 (wxid_tfxzqdqt87oa22)'

print(f'=== 查找消息内容包含 {target} 的消息 ===')

# 搜索 decompress 后的内容包含 wxid_tfxzqdqt87oa22 的消息
cur.execute(f"SELECT message_content, WCDB_CT_message_content, real_sender_id, create_time FROM [{table}] ORDER BY create_time DESC LIMIT 100")
rows = cur.fetchall()

found = 0
for row in rows:
    if row[0]:
        content = _decompress_content(row[0], row[1])
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='replace')
        if 'wxid_tfxzqdqt87oa22' in content or '印记' in content:
            print(f'real_sender_id={row[2]}')
            print(f'  {content[:300]}')
            print()
            found += 1
            if found >= 5:
                break

print(f'共找到 {found} 条相关消息')

conn.close()
