# -*- coding: utf-8 -*-
import sys
import os

sys.path.insert(0, r'E:\FHD\XCAGI')
sys.path.insert(0, r'E:\FHD\XCAGI\resources\wechat-decrypt')

from app.utils.path_utils import get_resource_path
from mcp_server import _decompress_content

def decompress(raw, ct):
    if not raw:
        return ""
    result = _decompress_content(raw, ct)
    if isinstance(result, bytes):
        return result.decode('utf-8', errors='replace')
    return result or ""

msg_db_path = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db'
wechat_id = 'wxid_tfxzqdqt87oa22'
numeric_id = 26  # contact.db 中的 id

import sqlite3
all_messages = []

conn = sqlite3.connect(msg_db_path)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")
tables = [row[0] for row in cur.fetchall()]
print(f"Tables: {len(tables)}")

# Step 1: Try numeric_id first (will fail, 26 != 98)
print(f"\nStep 1: Try numeric_id={numeric_id}")
found = False
for table in tables:
    try:
        cur.execute(f"PRAGMA table_info([{table}])")
        cols = [c[1] for c in cur.fetchall()]
        if 'real_sender_id' not in cols:
            continue
        cur.execute(f"SELECT message_content, WCDB_CT_message_content, create_time FROM [{table}] WHERE real_sender_id = ? ORDER BY create_time DESC LIMIT 10", [numeric_id, 10])
        rows = cur.fetchall()
        if rows:
            found = True
            print(f"  Found {len(rows)} messages in {table}")
            for row in rows:
                content = decompress(row[0], row[1]).strip()
                if content:
                    print(f"    {repr(content[:60])}")
    except Exception as e:
        continue
if not found:
    print("  No messages found with numeric_id")

# Step 2: Try content search with wxid (will fail, no wxid in content)
print(f"\nStep 2: Try content search with wxid='{wechat_id}'")
found = False
for table in tables:
    try:
        cur.execute(f"SELECT message_content, WCDB_CT_message_content, create_time FROM [{table}] ORDER BY create_time DESC LIMIT 500")
        rows = cur.fetchall()
        for row in rows:
            content = decompress(row[0], row[1]).strip()
            if content and wechat_id in content:
                found = True
                print(f"  Found in {table}: {repr(content[:60])}")
                break
    except Exception:
        continue
if not found:
    print("  No messages found with wxid in content")

# Step 3: Find single-sender tables (should find Msg_89707d4abce0cecdca50a8d0718b152b)
print(f"\nStep 3: Find single-sender tables")
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
            print(f"  Table {table} has single sender_id={sender_id}")
            # Get messages from this table
            cur.execute(f"SELECT message_content, WCDB_CT_message_content, create_time FROM [{table}] WHERE real_sender_id = ? ORDER BY create_time DESC LIMIT 10", [sender_id, 10])
            for msg_row in cur.fetchall():
                content = decompress(msg_row[0], msg_row[1]).strip()
                if content:
                    print(f"    {repr(content[:60])}")
    except Exception as e:
        print(f"  Error in {table}: {e}")

conn.close()