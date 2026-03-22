# -*- coding: utf-8 -*-
import sqlite3

msg_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db'
conn = sqlite3.connect(msg_db)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")
tables = [r[0] for r in cur.fetchall()]

print(f'目标联系人: wxid_tfxzqdqt87oa22, id=26')
print()

# real_sender_id = 26
target_id = 26
found = 0
for table in tables:
    try:
        cur.execute(f"SELECT COUNT(*) FROM [{table}] WHERE real_sender_id = ?", (target_id,))
        cnt = cur.fetchone()[0]
        if cnt > 0:
            print(f'表 {table}: {cnt} 条消息')
            found += cnt
            # 取一条样本
            cur.execute(f"SELECT message_content, create_time FROM [{table}] WHERE real_sender_id = ? ORDER BY create_time DESC LIMIT 1", (target_id,))
            row = cur.fetchone()
            if row:
                print(f'  最新消息: {row[0][:100] if row[0] else "None"}...')
    except Exception as e:
        print(f'表 {table} 错误: {e}')

print()
print(f'总共找到 {found} 条消息')
conn.close()
