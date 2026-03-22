# -*- coding: utf-8 -*-
import sqlite3

msg_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db'
conn = sqlite3.connect(msg_db)
cur = conn.cursor()

table = 'Msg_89707d4abce0cecdca50a8d0718b152b'

# 查找所有 real_sender_id 的样本
print('=== real_sender_id 样本 ===')
cur.execute(f"SELECT DISTINCT real_sender_id FROM [{table}] LIMIT 20")
ids = cur.fetchall()
print(f'real_sender_ids: {[r[0] for r in ids]}')

# 检查是否有表存储 sender 信息
print()
print('=== 查找其他可能的映射 ===')
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
all_tables = [r[0] for r in cur.fetchall()]
for t in all_tables:
    if 'Msg' not in t and 'name' not in t.lower():
        print(f'表: {t}')
        try:
            cur.execute(f"PRAGMA table_info([{t}])")
            cols = [c[1] for c in cur.fetchall()]
            print(f'  字段: {cols}')
        except:
            pass

conn.close()
