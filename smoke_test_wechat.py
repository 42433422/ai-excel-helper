# -*- coding: utf-8 -*-
import sqlite3
import os

msg_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db'
print(f'数据库: {msg_db}')
print(f'存在: {os.path.exists(msg_db)}')
print()

conn = sqlite3.connect(msg_db)
cur = conn.cursor()

# 1. 获取所有消息表
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")
tables = [r[0] for r in cur.fetchall()]
print(f'共有 {len(tables)} 个消息表')
print()

# 2. 查看第一个表的结构
cur.execute("PRAGMA table_info([{}])".format(tables[0]))
cols = cur.fetchall()
col_names = [c[1] for c in cols]
print(f'表结构: {col_names}')
print()

# 3. 查看所有 talker/real_sender_id
print('=== 查找 talker 字段数据 ===')
talker_col = 'talker' if 'talker' in col_names else 'real_sender_id'
cur.execute(f"SELECT DISTINCT {talker_col} FROM [{tables[0]}] LIMIT 20")
talkers = [r[0] for r in cur.fetchall()]
print(f'样本 talker: {talkers}')
print()

# 4. 搜索目标联系人
target = 'wxid_tfxzqdqt87oa22'
print(f'=== 搜索目标联系人: {target} ===')

# 先在 contact 表查一下
contact_db = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\contact\contact.db'
if os.path.exists(contact_db):
    conn2 = sqlite3.connect(contact_db)
    cur2 = conn2.cursor()
    cur2.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%Contact%'")
    ctables = [r[0] for r in cur2.fetchall()]
    print(f'联系人表: {ctables}')
    for ct in ctables:
        try:
            cur2.execute(f"SELECT * FROM [{ct}] WHERE UserName LIKE '%{target}%' OR NickName LIKE '%{target}%' LIMIT 5")
            rows = cur2.fetchall()
            if rows:
                print(f'在 {ct} 找到: {rows}')
        except:
            pass
    conn2.close()
else:
    print('contact.db 不存在')

# 5. 在所有消息表中搜索
print()
print('=== 在所有消息表中搜索 ===')
found_tables = []
for i, table in enumerate(tables):
    try:
        cur.execute(f"SELECT COUNT(*) FROM [{table}] WHERE {talker_col} = ?", (target,))
        cnt = cur.fetchone()[0]
        if cnt > 0:
            print(f'表 {table}: {cnt} 条消息')
            found_tables.append((table, cnt))
    except Exception as e:
        pass

if not found_tables:
    print('未找到任何消息!')
    print()
    print('尝试模糊搜索...')
    for table in tables[:5]:
        try:
            cur.execute(f"SELECT {talker_col} FROM [{table}] WHERE {talker_col} LIKE ? LIMIT 5", (f'%{target}%',))
            rows = cur.fetchall()
            if rows:
                print(f'{table}: {rows}')
        except:
            pass

conn.close()
