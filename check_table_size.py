# -*- coding: utf-8 -*-
import sqlite3

msg_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db'
conn = sqlite3.connect(msg_db)
cur = conn.cursor()

print('=== 消息表统计 ===')
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")
tables = [r[0] for r in cur.fetchall()]

total = 0
for t in tables:
    try:
        cur.execute(f"SELECT COUNT(*) FROM [{t}]")
        cnt = cur.fetchone()[0]
        total += cnt
        print(f'{t}: {cnt} 条')
    except:
        pass

print(f'\n总消息数: {total}')

# 测试在哪个表找到了印记
print('\n=== 测试在哪个表找到印记 ===')
for t in tables:
    try:
        cur.execute(f"SELECT COUNT(*) FROM [{t}] WHERE message_content LIKE '%wxid_tfxzqdqt87oa22%'")
        cnt = cur.fetchone()[0]
        if cnt > 0:
            print(f'{t}: {cnt} 条')
    except:
        pass

conn.close()
