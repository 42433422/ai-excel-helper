# -*- coding: utf-8 -*-
import sys
import os

sys.path.insert(0, r'E:\FHD\XCAGI')
from app.utils.path_utils import get_resource_path
import sqlite3

msg_db_path = os.path.join(get_resource_path("wechat-decrypt"), "decrypted", "message", "message_0.db")
print(f"msg_db: {msg_db_path}, exists: {os.path.exists(msg_db_path)}")

sys.path.insert(0, get_resource_path("wechat-decrypt"))
from mcp_server import _decompress_content

def decompress(raw, ct):
    if not raw:
        return ""
    if _decompress_content:
        result = _decompress_content(raw, ct)
        if isinstance(result, bytes):
            return result.decode('utf-8', errors='replace')
        return result or ""
    return raw.decode('utf-8', errors='replace') if isinstance(raw, bytes) else raw or ""

conn = sqlite3.connect(msg_db_path)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")
tables = [row[0] for row in cur.fetchall()]

# Find single-sender tables
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
            print(f"\nSingle-sender table: {table}, sender_id={sender_id}")
            cur.execute(f"SELECT message_content, WCDB_CT_message_content, create_time FROM [{table}] WHERE real_sender_id = ? ORDER BY create_time DESC LIMIT 10", [sender_id])
            for msg_row in cur.fetchall():
                content = decompress(msg_row[0], msg_row[1]).strip()
                print(f"  [{msg_row[2]}] ct={msg_row[1]}: {repr(content[:60])}")
    except Exception as e:
        print(f"Error in {table}: {e}")

conn.close()