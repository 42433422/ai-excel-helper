# -*- coding: utf-8 -*-
import sqlite3
import sys
import os

sys.path.insert(0, r'E:\FHD\XCAGI\resources\wechat-decrypt')
from mcp_server import _decompress_content

msg_dir = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message'
target = 'wxid_tfxzqdqt87oa22'

print(f'=== 在所有 message 数据库中搜索 {target} ===')

for db_file in os.listdir(msg_dir):
    if not db_file.endswith('.db'):
        continue
    msg_db = os.path.join(msg_dir, db_file)
    print(f'检查 {db_file}...')

    conn = sqlite3.connect(msg_db)
    cur = conn.cursor()

    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")
        tables = [r[0] for r in cur.fetchall()]

        for table in tables:
            try:
                cur.execute(f"SELECT message_content, WCDB_CT_message_content, real_sender_id, create_time FROM [{table}] ORDER BY create_time DESC LIMIT 100")
                rows = cur.fetchall()

                for row in rows:
                    if row[0]:
                        content = _decompress_content(row[0], row[1])
                        if isinstance(content, bytes):
                            content = content.decode('utf-8', errors='replace')
                        if target in content:
                            print(f'  在 {db_file} / {table} 中找到!')
                            print(f'    real_sender_id={row[2]}')
                            print(f'    {content[:200]}')
            except:
                pass
    except:
        pass

    conn.close()

print('搜索完成')
