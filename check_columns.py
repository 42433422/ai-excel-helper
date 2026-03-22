# -*- coding: utf-8 -*-
import sqlite3

msg_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db'
conn = sqlite3.connect(msg_db)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%' LIMIT 1")
tables = [r[0] for r in cur.fetchall()]

for table in tables:
    print(f'Table: {table}')
    cur.execute(f"PRAGMA table_info([{table}])")
    cols = cur.fetchall()
    print(f'Columns: {[c[1] for c in cols]}')

    cur.execute(f"SELECT * FROM [{table}] LIMIT 1")
    row = cur.fetchone()
    print(f'Sample row: {row}')

conn.close()
