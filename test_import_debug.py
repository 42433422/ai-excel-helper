# -*- coding: utf-8 -*-
import sys
import os

sys.path.insert(0, r'E:\FHD\XCAGI')
from app.utils.path_utils import get_resource_path

print(f"get_resource_path('wechat-decrypt'): {get_resource_path('wechat-decrypt')}")
print(f"exists: {os.path.exists(get_resource_path('wechat-decrypt'))}")

# Try importing the way the API does
sys.path.insert(0, get_resource_path("wechat-decrypt"))
print(f"sys.path[:3]: {sys.path[:3]}")

try:
    from mcp_server import _decompress_content
    print(f"Import succeeded: {_decompress_content}")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()

# Test decompress
import sqlite3
msg_db = os.path.join(get_resource_path("wechat-decrypt"), "decrypted", "message", "message_0.db")
conn = sqlite3.connect(msg_db)
cur = conn.cursor()
cur.execute("SELECT message_content, WCDB_CT_message_content FROM [Msg_89707d4abce0cecdca50a8d0718b152b] WHERE real_sender_id = 98 LIMIT 1")
row = cur.fetchone()
if row:
    raw, ct = row
    print(f"\nRow: ct={ct}, raw_len={len(raw) if raw else 0}")
    if '_decompress_content' in dir():
        result = _decompress_content(raw, ct)
        print(f"Decompress result: {repr(result[:50]) if result else None}")
conn.close()