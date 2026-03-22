# -*- coding: utf-8 -*-
import sqlite3
import sys

sys.path.insert(0, r'E:\FHD\XCAGI\resources\wechat-decrypt')
from mcp_server import _decompress_content

msg_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db'
conn = sqlite3.connect(msg_db)
cur = conn.cursor()

# 查找 wxid_tfxzqdqt87oa22 的消息（用模糊匹配 talker）
target = 'wxid_tfxzqdqt87oa22'
print(f'=== 查找 talker LIKE %{target}% 的消息 ===')
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")
tables = [r[0] for r in cur.fetchall()]

found = 0
for table in tables:
    try:
        cur.execute(f"SELECT message_content, WCDB_CT_message_content, create_time FROM [{table}] WHERE talker LIKE ? ORDER BY create_time DESC LIMIT 5", (f'%{target}%',))
        rows = cur.fetchall()
        for row in rows:
            if row[0]:
                content = _decompress_content(row[0], row[1])
                if content:
                    if isinstance(content, bytes):
                        content = content.decode('utf-8', errors='replace')
                    print(f'[{table}] talker LIKE %{target}%')
                    print(f'  {content[:300]}')
                    print()
                    found += 1
    except Exception as e:
        pass

print(f'共找到 {found} 条消息')

# 也查一下 id=26 的消息数
print()
print('=== real_sender_id=26 的消息 ===')
for table in tables:
    try:
        cur.execute(f"SELECT COUNT(*) FROM [{table}] WHERE real_sender_id = 26")
        cnt = cur.fetchone()[0]
        if cnt > 0:
            print(f'{table}: {cnt} 条')
    except:
        pass

conn.close()
