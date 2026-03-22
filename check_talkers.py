# -*- coding: utf-8 -*-
import sqlite3

msg_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db'
conn = sqlite3.connect(msg_db)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%' LIMIT 3")
tables = [r[0] for r in cur.fetchall()]

for table in tables:
    cur.execute(f"SELECT talker FROM [{table}] GROUP BY talker LIMIT 5")
    talkers = [r[0] for r in cur.fetchall()]
    print(f'{table}: {talkers}')

conn.close()
