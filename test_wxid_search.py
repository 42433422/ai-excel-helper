# -*- coding: utf-8 -*-
import sys
import os

sys.path.insert(0, r'E:\FHD\XCAGI\resources\wechat-decrypt')
from mcp_server import _decompress_content

msg_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db'
wechat_id = 'wxid_tfxzqdqt87oa22'  # 印记的 wxid

import sqlite3
conn = sqlite3.connect(msg_db)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")
tables = [r[0] for r in cur.fetchall()]

print(f"搜索包含 wxid '{wechat_id}' 的消息:\n")

found = []
for tbl in tables:
    try:
        cur.execute(f"SELECT message_content, WCDB_CT_message_content, create_time FROM [{tbl}] ORDER BY create_time DESC LIMIT 500")
        for row in cur.fetchall():
            raw = row[0]
            ct = row[1]
            if not raw:
                continue
            content = _decompress_content(raw, ct) if ct and ct > 0 else raw
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='replace')
            content = (content or "").strip()
            if not content:
                continue
            if wechat_id in content:
                found.append((tbl, row[2], content))
                print(f"找到! 表: {tbl}, 时间: {row[2]}")
                print(f"  内容: {repr(content[:100])}")
    except Exception as e:
        continue

print(f"\n总计找到 {len(found)} 条消息包含 wxid")
conn.close()