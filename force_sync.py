# -*- coding: utf-8 -*-
import sys, os, glob, json, shutil
sys.path.insert(0, r'E:\FHD\XCAGI\resources\wechat-decrypt')
from config import load_config
from key_utils import get_key_info, strip_key_metadata
from decrypt_db import decrypt_database

cfg = load_config()
db_dir = cfg.get('db_dir')
raw_db_dir = r'E:\FHD\XCAGI\resources\wechat-decrypt\raw_db'
decrypted_dir = cfg.get('decrypted_dir')

print('=== 强制复制和解密 ===')

# 1. 强制复制
raw_msg_dir = os.path.join(raw_db_dir, 'message')
src_msg = os.path.join(db_dir, 'message')
os.makedirs(raw_msg_dir, exist_ok=True)
shutil.rmtree(raw_msg_dir)
os.makedirs(raw_msg_dir)

copy_count = 0
for f in glob.glob(os.path.join(src_msg, '*.db')):
    if f.endswith('-wal') or f.endswith('-shm'):
        continue
    shutil.copy2(f, raw_msg_dir)
    copy_count += 1
print(f'1. 已复制 {copy_count} 个文件到 raw_db')

# 2. 强制解密
with open(cfg.get('keys_file'), 'r', encoding='utf-8') as f:
    keys = json.load(f)
keys = strip_key_metadata(keys)

decrypted_msg_dir = os.path.join(decrypted_dir, 'message')
os.makedirs(decrypted_msg_dir, exist_ok=True)
shutil.rmtree(decrypted_msg_dir)
os.makedirs(decrypted_msg_dir)

decrypt_count = 0
for raw_path in glob.glob(os.path.join(raw_msg_dir, '*.db')):
    rel = os.path.relpath(raw_path, raw_msg_dir)
    dec_path = os.path.join(decrypted_msg_dir, rel)
    key_info = get_key_info(keys, os.path.join('message', rel))
    if key_info:
        result = decrypt_database(raw_path, dec_path, bytes.fromhex(key_info['enc_key']))
        if result:
            decrypt_count += 1
            print(f'   解密: {rel}')
print(f'2. 已解密 {decrypt_count} 个文件')

# 3. 检查联系人消息
print('3. 检查 wxid_tfxzqdqt87oa22 的消息...')
import sqlite3
msg_db = os.path.join(decrypted_msg_dir, 'message_0.db')
conn = sqlite3.connect(msg_db)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")
tables = [r[0] for r in cur.fetchall()]
print(f'   共有 {len(tables)} 个消息表')

found = 0
for table in tables:
    try:
        cur.execute(f'SELECT COUNT(*) FROM [{table}] WHERE talker = ?', ('wxid_tfxzqdqt87oa22',))
        cnt = cur.fetchone()[0]
        if cnt > 0:
            print(f'   表 {table} 有 {cnt} 条消息')
            found += cnt
    except:
        pass
print(f'   总共找到 {found} 条消息')
conn.close()
