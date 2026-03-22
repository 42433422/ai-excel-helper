# -*- coding: utf-8 -*-
import sqlite3

msg_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db'
conn = sqlite3.connect(msg_db)
cur = conn.cursor()

# 查找所有包含 id 或 name 的表
print('=== 查找映射表 ===')
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE '%Id%' OR name LIKE '%id%' OR name LIKE '%Name%' OR name LIKE '%name%' OR name LIKE '%Contact%' OR name LIKE '%contact%' OR name LIKE '%User%' OR name LIKE '%user%')")
tables = cur.fetchall()
print(f'候选表: {[t[0] for t in tables]}')

for t in tables:
    print(f'\n=== {t[0]} ===')
    try:
        cur.execute(f"PRAGMA table_info([{t[0]}])")
        cols = [c[1] for c in cur.fetchall()]
        print(f'字段: {cols}')
        cur.execute(f"SELECT * FROM [{t[0]}] LIMIT 5")
        rows = cur.fetchall()
        for r in rows:
            print(f'  {r}')
    except Exception as e:
        print(f'错误: {e}')

conn.close()
