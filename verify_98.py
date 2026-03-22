# -*- coding: utf-8 -*-
import sqlite3
import sys

sys.path.insert(0, r'E:\FHD\XCAGI\resources\wechat-decrypt')
from mcp_server import _decompress_content

contact_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\contact\contact.db'
msg_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db'

conn = sqlite3.connect(contact_db)
cur = conn.cursor()

# 检查 stranger 表
print("stranger 表结构:")
cur.execute("PRAGMA table_info(stranger)")
for c in cur.fetchall():
    print(f"  {c[1]}: {c[2]}")

print("\nstranger 表中 username 字段包含 wxid_tfxzqdqt87oa22 的行:")
cur.execute("SELECT * FROM stranger WHERE username = 'wxid_tfxzqdqt87oa22'")
rows = cur.fetchall()
for r in rows:
    print(f"  {r}")

print("\nstranger 前5行:")
cur.execute("SELECT * FROM stranger LIMIT 5")
for r in cur.fetchall():
    print(f"  {r}")

conn.close()

# 检查 Msg_89707d4abce0cecdca50a8d0718b152b 表的消息 talker 字段
print("\n" + "=" * 60)
print("检查 Msg_89707d4abce0cecdca50a8d0718b152b 的 talker:")
conn = sqlite3.connect(msg_db)
cur = conn.cursor()
# 这个表没有 talker 列，但检查是否有 strng 表
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stranger'")
if cur.fetchone():
    print("Has stranger table")
    cur.execute("SELECT * FROM stranger LIMIT 5")
    for r in cur.fetchall():
        print(f"  {r}")
else:
    print("No stranger table in message db")

# 关键: 检查所有消息表，看是否有包含 wxid_tfxzqdqt87oa22 文本内容的
# 而不是 xmlmsg 中包含的
print("\n搜索纯文本消息内容包含 wxid_tfxzqdqt87oa22 的:")
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")
tables = [r[0] for r in cur.fetchall()]

found_text = []
for tbl in tables:
    try:
        cur.execute(f"SELECT message_content, WCDB_CT_message_content, real_sender_id FROM [{tbl}] WHERE WCDB_CT_message_content = 0 LIMIT 50")
        for row in cur.fetchall():
            raw = row[0]
            ct = row[1]
            if not raw:
                continue
            content = _decompress_content(raw, ct) if ct and ct > 0 else raw
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='replace')
            if content and 'wxid_tfxzqdqt87oa22' in content and not content.startswith('<'):
                found_text.append((tbl, row[2], content))
    except Exception as e:
        print(f"Error in {tbl}: {e}")

if found_text:
    for item in found_text[:10]:
        print(f"  {item[0]}, sender={item[1]}: {repr(item[2][:80])}")
else:
    print("  No plain text messages contain wxid_tfxzqdqt87oa22")

conn.close()