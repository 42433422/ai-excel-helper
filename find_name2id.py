# -*- coding: utf-8 -*-
import sqlite3

msg_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db'
conn = sqlite3.connect(msg_db)
cur = conn.cursor()

print('=== 查找 Name2Id 相关表 ===')
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE '%Name%' OR name LIKE '%name%' OR name LIKE '%Id%' OR name LIKE '%id%')")
tables = cur.fetchall()
print(f'相关表: {[t[0] for t in tables]}')

for t in tables:
    print(f'\n=== {t[0]} 表 ===')
    try:
        cur.execute(f"PRAGMA table_info([{t[0]}])")
        cols = cur.fetchall()
        print(f'字段: {[c[1] for c in cols]}')
        cur.execute(f"SELECT * FROM [{t[0]}] LIMIT 10")
        rows = cur.fetchall()
        for r in rows:
            print(f'  {r}')
    except Exception as e:
        print(f'错误: {e}')

conn.close()
