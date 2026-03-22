# -*- coding: utf-8 -*-
# Direct test of _query_messages_by_numeric_id logic

import sys
import os

sys.path.insert(0, r'E:\FHD\XCAGI')
from app.utils.path_utils import get_resource_path

msg_db_path = os.path.join(get_resource_path("wechat-decrypt"), "decrypted", "message", "message_0.db")
print(f"msg_db: {msg_db_path}, exists: {os.path.exists(msg_db_path)}")

wechat_id = 'wxid_tfxzqdqt87oa22'
numeric_id = None  # We passed None
limit = 50

import sqlite3
all_messages = []
try:
    sys.path.insert(0, get_resource_path("wechat-decrypt"))
    from mcp_server import _decompress_content
    print(f"_decompress_content: {_decompress_content}")
except Exception as e:
    print(f"Import error: {e}")
    _decompress_content = None

def decompress(raw, ct):
    if not raw:
        return ""
    if _decompress_content:
        result = _decompress_content(raw, ct)
        if isinstance(result, bytes):
            return result.decode('utf-8', errors='replace')
        return result or ""
    return raw.decode('utf-8', errors='replace') if isinstance(raw, bytes) else raw or ""

try:
    conn = sqlite3.connect(msg_db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")
    tables = [row[0] for row in cur.fetchall()]
    print(f"Tables: {len(tables)}")

    if numeric_id:
        print("Step 1: numeric_id query (skipped since numeric_id is None)")

    if not all_messages and wechat_id:
        print("\nStep 2: Content search with wxid")
        for table in tables:
            try:
                cur.execute(f"SELECT message_content, WCDB_CT_message_content, create_time FROM [{table}] ORDER BY create_time DESC LIMIT 500")
                rows = cur.fetchall()
                for row in rows:
                    content = decompress(row[0], row[1]).strip()
                    if not content or wechat_id not in content:
                        continue
                    all_messages.append({"role": "other", "text": content})
                    if len(all_messages) >= limit:
                        break
                if len(all_messages) >= limit:
                    break
            except Exception as e:
                print(f"  Error in {table}: {e}")
                continue

    if not all_messages:
        print("\nStep 3: Single-sender tables fallback")
        for table in tables:
            try:
                cur.execute(f"PRAGMA table_info([{table}])")
                cols = [c[1] for c in cur.fetchall()]
                if 'real_sender_id' not in cols:
                    continue
                cur.execute(f"SELECT real_sender_id, COUNT(DISTINCT real_sender_id) FROM [{table}]")
                row = cur.fetchone()
                if row and row[1] == 1:
                    sender_id = row[0]
                    print(f"  Found single-sender table {table} with sender_id={sender_id}")
                    cur.execute(f"SELECT message_content, WCDB_CT_message_content, create_time FROM [{table}] WHERE real_sender_id = ? ORDER BY create_time DESC LIMIT {limit}", [sender_id])
                    for msg_row in cur.fetchall():
                        content = decompress(msg_row[0], msg_row[1]).strip()
                        if not content:
                            continue
                        all_messages.append({"role": "other", "text": content})
                        if len(all_messages) >= limit:
                            break
                    if all_messages:
                        break
            except Exception as e:
                print(f"  Error in {table}: {e}")
                continue

    conn.close()
except Exception as e:
    print(f"Outer error: {e}")

print(f"\nTotal messages: {len(all_messages)}")
for i, msg in enumerate(all_messages[:5]):
    print(f"\n[{i}]: {repr(msg['text'][:80])}")