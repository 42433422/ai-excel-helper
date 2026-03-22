# -*- coding: utf-8 -*-
import sys
import os

sys.path.insert(0, r'E:\FHD\XCAGI')
from app.utils.path_utils import get_resource_path

msg_db_path = os.path.join(get_resource_path("wechat-decrypt"), "decrypted", "message", "message_0.db")
wechat_id = 'wxid_tfxzqdqt87oa22'

sys.path.insert(0, get_resource_path("wechat-decrypt"))
from mcp_server import _decompress_content

import sqlite3
all_messages = []

conn = sqlite3.connect(msg_db_path)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")
tables = [r[0] for r in cur.fetchall()]

for table in tables:
    try:
        cur.execute(f"SELECT message_content, WCDB_CT_message_content, create_time FROM [{table}] ORDER BY create_time DESC LIMIT 2000")
        rows = cur.fetchall()
        for row in rows:
            raw_content = row[0]
            ct = row[1]
            if not raw_content:
                continue
            content = _decompress_content(raw_content, ct) if _decompress_content else raw_content
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='replace') if content else ''
            content = (content or "").strip()
            if not content:
                continue
            if wechat_id in content or (content.startswith('<') and wechat_id in content):
                all_messages.append({"role": "other", "text": content})
            if len(all_messages) >= 50:
                break
        if len(all_messages) >= 50:
            break
    except Exception as e:
        continue

conn.close()

print(f"Found {len(all_messages)} messages")
for i, msg in enumerate(all_messages[:5]):
    print(f"\n[{i}]: {repr(msg['text'][:100])}")