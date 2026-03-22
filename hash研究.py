# -*- coding: utf-8 -*-
# 研究 Msg_<hash> 表名的生成规则
# 看看 hash 是否可能和 wxid 或 real_sender_id 相关

import hashlib

# 可能的 hash 来源
wxid = 'wxid_tfxzqdqt87oa22'
sender_id = '98'

# 测试不同的 hash 方式
test_strings = [
    wxid,
    wxid.lower(),
    wxid.upper(),
    sender_id,
    f"wechat_{wxid}",
    f"msg_{wxid}",
    f"{wxid}_session",
    sender_id.encode().hex(),
]

# 实际的 hash 前缀
target_prefix = '89707d4abce0cecdca50a8d0718b152b'
print(f"Looking for hash starting with: {target_prefix[:8]}...")
print()

# 实际的表名 hash
print(f"Actual table: Msg_{target_prefix}")
print()

# 尝试用不同的方式生成 hash
for s in test_strings:
    h = hashlib.md5(s.encode()).hexdigest()
    print(f"md5('{s}') = {h}")

# 尝试用 sender_id 98 生成
h = hashlib.md5(b'98').hexdigest()
print(f"\nmd5('98' bytes) = {h}")

# 尝试和 wxid 组合
h = hashlib.md5(wxid.encode('utf-8')).hexdigest()
print(f"md5(wxid utf8) = {h}")

# 看起来 89707d4abce0cecdca50a8d0718b152b 不是直接从 wxid 生成的
# 让我看看是否有其他表名

# 查看所有 Msg 表
import sys
import os
sys.path.insert(0, r'E:\FHD\XCAGI\resources\wechat-decrypt')
import sqlite3
msg_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db'
conn = sqlite3.connect(msg_db)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
print(f"\n\nAll {len(tables)} Msg tables:")
for t in tables:
    print(f"  {t}")
conn.close()