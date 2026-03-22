# -*- coding: utf-8 -*-
import sys
import os

sys.path.insert(0, r'E:\FHD\XCAGI\resources\wechat-decrypt')
import sqlite3

resource_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_resource.db'

conn = sqlite3.connect(resource_db)
cur = conn.cursor()

# Check MessageResourceDetail structure in detail
print("=== MessageResourceDetail sample (first 5) ===")
cur.execute("SELECT resource_id, message_id, type, size, create_time, status, data_index, packed_info FROM MessageResourceDetail LIMIT 5")
for row in cur.fetchall():
    resource_id, message_id, type_, size, create_time, status, data_index, packed_info = row
    print(f"\nresource_id={resource_id}, message_id={message_id}, type={type_}, size={size}, status={status}")
    print(f"  data_index: {data_index[:50] if data_index else None}...")
    print(f"  packed_info length: {len(packed_info) if packed_info else 0}")

# Check what types exist
print("\n\n=== Type distribution ===")
cur.execute("SELECT type, COUNT(*) FROM MessageResourceDetail GROUP BY type")
for row in cur.fetchall():
    print(f"  type {row[0]}: {row[1]} rows")

# Try to find resource by size (image size was 1114891 bytes)
print("\n\n=== Looking for resource with size ~1114891 ===")
cur.execute("SELECT resource_id, message_id, type, size, data_index FROM MessageResourceDetail WHERE size > 1000000 AND size < 2000000")
rows = cur.fetchall()
print(f"Found {len(rows)} resources with size 1-2MB")
for r in rows[:5]:
    print(f"  {r}")

conn.close()