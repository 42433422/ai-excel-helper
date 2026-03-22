# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'E:\FHD\XCAGI\resources\wechat-decrypt')
from mcp_server import _decompress_content

# Test with full bytes from db
test_bytes = b'(\xb5/\xfd`\x00\x04\xad\x14\x00f\xaa\x83&\xf0\xac\xcc\x03\xd3\xdeZ\xc3\xd4\xc1>\xe0\xa7+^d'
result = _decompress_content(test_bytes, 4)
print(f"Test 1 (partial): {repr(result) if result else None}")

# Test with actual bytes from db row 1
import sqlite3
msg_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db'
conn = sqlite3.connect(msg_db)
cur = conn.cursor()
cur.execute("SELECT message_content, WCDB_CT_message_content FROM [Msg_89707d4abce0cecdca50a8d0718b152b] WHERE real_sender_id = 98 AND local_id = 1")
row = cur.fetchone()
conn.close()

if row:
    raw = row[0]
    ct = row[1]
    print(f"\nRaw bytes type: {type(raw)}, length: {len(raw) if raw else 0}")
    print(f"Raw bytes (first 50): {raw[:50] if raw else None}")
    print(f"ct = {ct}")
    result = _decompress_content(raw, ct)
    print(f"Decompress result type: {type(result)}")
    print(f"Decompress result: {repr(result[:100]) if result else None}")

# Check if raw is memoryview or bytes
print(f"\nIs bytes: {isinstance(raw, bytes)}")
print(f"Is memoryview: {isinstance(raw, memoryview)}")
if isinstance(raw, memoryview):
    print(f"Converting to bytes...")
    raw = bytes(raw)
    result = _decompress_content(raw, ct)
    print(f"Result after convert: {repr(result[:100]) if result else None}")